from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.http import JsonResponse, FileResponse
from django.conf import settings
from django.contrib import messages
from django.utils.html import format_html
import os
import uuid
import docx

from apps.history.models import PlagiarismHistory, UserUploadQuota
from .models import PlagiarismSettings
from .forms import PlagiarismCheckForm
from .tasks import PlagiarismTask

@admin.register(PlagiarismSettings)
class PlagiarismSettingsAdmin(admin.ModelAdmin):
    list_display = ('similarity_threshold', 'auto_delete_days', 'updated_at')
    fieldsets = (
        ('Pengaturan Deteksi', {
            'fields': ('similarity_threshold',),
            'description': 'Atur threshold minimum untuk mendeteksi plagiarisme'
        }),
        ('Pengaturan Pembersihan Otomatis', {
            'fields': ('auto_delete_days',),
            'description': 'Laporan akan dihapus otomatis setelah N hari. Isi 0 untuk menonaktifkan auto-delete.'
        }),
    )
    
    def has_add_permission(self, request):
        return not PlagiarismSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(PlagiarismHistory)
class PlagiarismHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'filename', 
        'user', 
        'similarity_display',
        'status', 
        'file_status_display',
        'check_date'
    )
    list_filter = ('status', 'source_mode', 'file_deleted', 'check_date', 'user')
    search_fields = ('filename', 'user__username')
    readonly_fields = (
        'check_date', 'started_at', 'completed_at', 'report_file', 
        'similarity_score', 'similarity_local', 'similarity_internet',
        'matched_sources_display',
        'filename', 'user', 'source_mode', 'status', 
        'progress', 'error_message',
        'file_deleted', 'file_deleted_at', 'file_deleted_reason'
    )
    
    change_list_template = "admin/plagiarism/change_list_history.html"
    
    fieldsets = (
        ('Informasi Dokumen', {
            'fields': ('filename', 'user', 'check_date', 'source_mode')
        }),
        ('Status Pemrosesan', {
            'fields': ('status', 'progress', 'started_at', 'completed_at', 'error_message')
        }),
        ('Hasil Deteksi', {
            'fields': ('similarity_score', 'similarity_local', 'similarity_internet', 'matched_sources_display')
        }),
        ('File & Laporan', {
            'fields': ('report_file', 'file_deleted', 'file_deleted_at', 'file_deleted_reason')
        }),
    )
    
    def similarity_display(self, obj):
        """Display similarity dengan breakdown"""
        if obj.similarity_score is not None:
            return f"🌐 {obj.similarity_score}% (L:{obj.similarity_local or 0}% | I:{obj.similarity_internet or 0}%)"
        return "-"
    similarity_display.short_description = "Similaritas"
    
    def matched_sources_display(self, obj):
        """Display matched sources dengan metadata dan role-based access"""
        sources = obj.get_matched_sources()
        if not sources:
            return format_html('<p class="text-muted"><i>Tidak ada sumber terdeteksi</i></p>')
        
        # Get current user's role
        from django.contrib.auth import get_user
        from threading import current_thread
        
        # Get request from thread local (ini adalah workaround untuk mendapatkan request di admin)
        # Alternatif: bisa juga menggunakan middleware custom
        user_role = obj.user.role if hasattr(obj, 'user') else 'mahasiswa'
        
        html = '<div style="max-height: 400px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; background: #f9f9f9;">'
        
        # Local sources
        if 'local' in sources and sources['local']:
            html += '<h4 style="color: #2c3e50; margin-top: 0;">📚 Repository Lokal:</h4>'
            html += '<div style="margin-bottom: 20px;">'
            
            for src in sources['local']:
                html += '<div style="background: white; padding: 10px; margin-bottom: 10px; border-left: 4px solid #3498db; border-radius: 4px;">'
                html += f'<div style="font-weight: bold; color: #2c3e50; margin-bottom: 5px;">📄 {src["title"]}</div>'
                html += f'<div style="color: #7f8c8d; font-size: 0.9em; margin-bottom: 5px;">'
                html += f'👤 <strong>Penulis:</strong> {src["author"]} | '
                html += f'📅 <strong>Tahun:</strong> {src["year"]}<br>'
                html += f'🔍 <strong>Kalimat Terdeteksi:</strong> {src["count"]} kalimat'
                html += '</div>'
                
                # Role-based file access
                if user_role in ['superadmin', 'staff']:
                    if src.get('file_path') and os.path.exists(src['file_path']):
                        # Link to repository file detail page
                        repo_url = f'/admin/repository/repositoryfile/{src["id"]}/change/'
                        html += f'<a href="{repo_url}" target="_blank" style="display: inline-block; margin-top: 5px; padding: 5px 10px; background: #27ae60; color: white; text-decoration: none; border-radius: 3px; font-size: 0.85em;">🔓 Buka File Sumber</a>'
                    else:
                        html += '<span style="color: #e74c3c; font-size: 0.85em;">⚠️ File tidak ditemukan</span>'
                else:
                    html += '<span style="color: #95a5a6; font-size: 0.85em;">🔒 Akses file terbatas untuk staff/admin</span>'
                
                html += '</div>'
            
            html += '</div>'
        
        # Internet sources
        if 'internet' in sources and sources['internet']:
            html += '<h4 style="color: #2c3e50; margin-top: 10px;">🌐 Sumber Internet:</h4>'
            html += '<div style="margin-bottom: 10px;">'
            
            # Limit display to first 15 URLs
            displayed_urls = sources['internet'][:15]
            remaining = len(sources['internet']) - 15
            
            for idx, url in enumerate(displayed_urls, 1):
                # Truncate long URLs
                display_url = url if len(url) <= 80 else url[:77] + '...'
                
                html += '<div style="background: white; padding: 8px; margin-bottom: 5px; border-left: 4px solid #e67e22; border-radius: 4px;">'
                html += f'<span style="color: #7f8c8d; font-size: 0.85em; margin-right: 8px;">{idx}.</span>'
                html += f'<a href="{url}" target="_blank" rel="noopener noreferrer" style="color: #3498db; text-decoration: none; word-break: break-all;">'
                html += f'{display_url}'
                html += '</a>'
                html += '</div>'
            
            if remaining > 0:
                html += f'<div style="color: #95a5a6; font-style: italic; margin-top: 10px; text-align: center;">+ {remaining} sumber lainnya tidak ditampilkan</div>'
            
            html += '</div>'
        
        html += '</div>'
        
        # Add legend
        html += '<div style="margin-top: 10px; padding: 8px; background: #ecf0f1; border-radius: 4px; font-size: 0.85em; color: #7f8c8d;">'
        html += '<strong>Keterangan:</strong><br>'
        html += '• <strong>Repository Lokal:</strong> Sumber dari database internal<br>'
        html += '• <strong>Sumber Internet:</strong> Link website yang terdeteksi similar<br>'
        if user_role == 'mahasiswa':
            html += '• 🔒 Mahasiswa hanya dapat melihat metadata, tidak dapat mengakses file sumber'
        else:
            html += '• 🔓 Staff/Admin dapat membuka file sumber dari repository'
        html += '</div>'
        
        return format_html(html)
    
    matched_sources_display.short_description = "Sumber Terdeteksi"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.role == 'superadmin'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('start-check/', self.admin_site.admin_view(self.plagiarism_check_view), 
                 name='plagiarism_check_tool'),
            path('check-status/', self.admin_site.admin_view(self.check_status), 
                 name='plagiarism_check_status'),
            path('download-report/<uuid:history_id>/', self.admin_site.admin_view(self.download_report), 
                 name='plagiarism_download_report'),
        ]
        return custom_urls + urls

    def file_status_display(self, obj):
        if obj.file_deleted:
            return "🗑️ File Dihapus"
        elif obj.status == 'completed' and obj.report_file:
            return "✅ Tersedia"
        else:
            return "⏳ Belum Ada"
    file_status_display.short_description = "Status File"

    def plagiarism_check_view(self, request):
        context = dict(self.admin_site.each_context(request))
        
        # Check quota
        remaining_quota = UserUploadQuota.get_remaining_quota(request.user)
        context['remaining_quota'] = remaining_quota
        
        # Check active process
        active_process = PlagiarismHistory.objects.filter(
            user=request.user,
            status__in=['pending', 'processing']
        ).first()
        
        context['active_process'] = active_process

        if request.method == 'POST':
            if active_process:
                messages.warning(request, "⚠️ Anda masih memiliki proses yang sedang berjalan.")
                return redirect('admin:plagiarism_check_tool')
            
            form = PlagiarismCheckForm(request.POST, request.FILES)
            
            if form.is_valid():
                try:
                    input_type = form.cleaned_data['input_type']
                    source_mode = form.cleaned_data['source_mode']
                    
                    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
                    os.makedirs(temp_dir, exist_ok=True)
                    
                    files_to_process = []
                    
                    if input_type == 'file':
                        uploaded_files = request.FILES.getlist('document_file')
                        
                        if not uploaded_files:
                            messages.error(request, "❌ Tidak ada file yang diupload.")
                            return redirect('admin:plagiarism_check_tool')
                        
                        if len(uploaded_files) > remaining_quota:
                            messages.error(
                                request, 
                                f"❌ Kuota harian Anda: {remaining_quota}. "
                                f"Tidak bisa upload {len(uploaded_files)} file."
                            )
                            return redirect('admin:plagiarism_check_tool')
                        
                        for uploaded_file in uploaded_files:
                            file_ext = os.path.splitext(uploaded_file.name)[1].lower()
                            
                            if file_ext not in ['.docx', '.pdf']:
                                messages.warning(
                                    request, 
                                    f"⚠️ File '{uploaded_file.name}' diabaikan (format tidak didukung)."
                                )
                                continue
                            
                            max_size = 10 * 1024 * 1024
                            if uploaded_file.size > max_size:
                                messages.warning(
                                    request,
                                    f"⚠️ File '{uploaded_file.name}' terlalu besar."
                                )
                                continue
                            
                            safe_filename = self._sanitize_filename(uploaded_file.name)
                            temp_filename = f"{uuid.uuid4()}{file_ext}"
                            temp_path = os.path.join(temp_dir, temp_filename)
                            
                            try:
                                with open(temp_path, 'wb+') as destination:
                                    for chunk in uploaded_file.chunks():
                                        destination.write(chunk)
                                
                                files_to_process.append({
                                    'filename': safe_filename,
                                    'temp_path': temp_path
                                })
                            except Exception as e:
                                messages.error(request, f"❌ Error: {str(e)}")
                                continue
                    
                    else:  # text input
                        if remaining_quota < 1:
                            messages.error(request, "❌ Kuota harian Anda habis.")
                            return redirect('admin:plagiarism_check_tool')
                        
                        raw_text = form.cleaned_data['pasted_text']
                        
                        if not raw_text or len(raw_text.strip()) < 100:
                            messages.error(request, "❌ Teks terlalu pendek.")
                            return redirect('admin:plagiarism_check_tool')
                        
                        temp_path = os.path.join(temp_dir, f"{uuid.uuid4()}.docx")
                        
                        try:
                            doc = docx.Document()
                            for paragraph in raw_text.split('\n'):
                                if paragraph.strip():
                                    doc.add_paragraph(paragraph.strip())
                            doc.save(temp_path)
                            
                            files_to_process.append({
                                'filename': "pasted_text.docx",
                                'temp_path': temp_path
                            })
                        except Exception as e:
                            messages.error(request, f"❌ Error: {str(e)}")
                            return redirect('admin:plagiarism_check_tool')
                    
                    if not files_to_process:
                        messages.error(request, "❌ Tidak ada file valid.")
                        return redirect('admin:plagiarism_check_tool')
                    
                    UserUploadQuota.increment_quota(request.user, len(files_to_process))
                    
                    for file_info in files_to_process:
                        history = PlagiarismHistory.objects.create(
                            user=request.user,
                            filename=file_info['filename'],
                            source_mode=source_mode,
                            status='pending',
                            progress=0
                        )
                        
                        PlagiarismTask.process_document(
                            history.id,
                            file_info['temp_path'],
                            source_mode
                        )
                    
                    messages.success(
                        request, 
                        f"✅ {len(files_to_process)} dokumen berhasil dikirim untuk diproses."
                    )
                    return redirect('admin:plagiarism_check_tool')
                    
                except Exception as e:
                    messages.error(request, f"❌ Terjadi kesalahan: {str(e)}")
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
        else:
            form = PlagiarismCheckForm()

        context['form'] = form
        context['title'] = "Alat Cek Plagiasi Dokumen"
        return render(request, 'admin/plagiarism/check_plagiarism.html', context)

    def _sanitize_filename(self, filename):
        filename = os.path.basename(filename)
        import re
        filename = re.sub(r'[^\w\s\-\.]', '', filename)
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:190] + ext
        return filename

    def check_status(self, request):
        active_process = PlagiarismHistory.objects.filter(
            user=request.user,
            status__in=['pending', 'processing']
        ).first()
        
        recent_processes = PlagiarismHistory.objects.filter(
            user=request.user
        ).order_by('-check_date')[:5]
        
        data = {
            'has_active': bool(active_process),
            'remaining_quota': UserUploadQuota.get_remaining_quota(request.user),
            'processes': []
        }
        
        for process in recent_processes:
            data['processes'].append({
                'id': str(process.id),
                'filename': process.filename,
                'status': process.status,
                'progress': process.progress,
                'similarity_score': process.similarity_score,
                'error_message': process.error_message,
                'file_deleted': process.file_deleted,
                'file_deleted_reason': process.file_deleted_reason,
                'can_download': bool(
                    process.status == 'completed' 
                    and process.report_file 
                    and not process.file_deleted
                    and os.path.exists(process.report_file.path)
                )
            })
        
        return JsonResponse(data)
  
    def download_report(self, request, history_id):
        try:
            history = PlagiarismHistory.objects.get(id=history_id, user=request.user)
            
            if history.file_deleted:
                messages.error(
                    request, 
                    f"❌ File sudah dihapus pada {history.file_deleted_at.strftime('%d-%m-%Y')}. "
                    f"Alasan: {history.file_deleted_reason}"
                )
                return redirect('admin:plagiarism_check_tool')
            
            if history.status != 'completed' or not history.report_file:
                messages.error(request, "Laporan belum tersedia")
                return redirect('admin:plagiarism_check_tool')
            
            file_path = history.report_file.path
            
            if not os.path.exists(file_path):
                from django.utils import timezone
                history.file_deleted = True
                history.file_deleted_at = timezone.now()
                history.file_deleted_reason = 'File not found'
                history.save()
                
                messages.error(request, "File laporan tidak ditemukan")
                return redirect('admin:plagiarism_check_tool')
            
            filename = f"RESULT_{os.path.splitext(history.filename)[0]}.pdf"
            
            response = FileResponse(
                open(file_path, 'rb'),
                as_attachment=True,
                filename=filename,
                content_type='application/pdf'
            )
            return response
            
        except PlagiarismHistory.DoesNotExist:
            messages.error(request, "Laporan tidak ditemukan")
            return redirect('admin:plagiarism_check_tool')