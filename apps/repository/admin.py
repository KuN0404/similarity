from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from apps.plagiarism.decorators import permission_required_custom, superadmin_required
import os
import fitz  # PyMuPDF
import docx
from .models import RepositoryFile

@admin.register(RepositoryFile)
class RepositoryFileAdmin(admin.ModelAdmin):
    list_display = ('filename', 'basename', 'status', 'index_date', 'size_bytes')
    list_filter = ('status', 'filetype')
    search_fields = ('filename', 'basename')
    
    readonly_fields = (
        'id', 
        'filename', 
        'basename', 
        'filetype', 
        'extracted_text_path', 
        'size_bytes', 
        'extracted_text_length', 
        'index_date', 
        'status', 
        'error_message'
    )

    # Grouping fields for better layout
    fieldsets = (
        ('Upload Document', {
            'fields': ('file', 'title', 'author', 'year')
        }),
        ('System Information (Auto-Filled)', {
            'fields': ('id', 'filename', 'basename', 'filetype', 'status', 'index_date'),
            'classes': ('collapse',)  # This makes the section collapsible/hidden by default
        }),
        ('Indexing Details (Auto-Filled)', {
            'fields': ('extracted_text_path', 'size_bytes', 'extracted_text_length', 'error_message'),
            'classes': ('collapse',)
        }),
    )

    # ------------------------------

    actions = ['start_indexing_action']
    change_list_template = "admin/repository/change_list_with_index_button.html"

    def has_add_permission(self, request):
        return request.user.has_perm('accounts.can_add_repository')
    
    def has_change_permission(self, request, obj=None):
        return request.user.has_perm('accounts.can_edit_repository')
    
    def has_delete_permission(self, request, obj=None):
        return request.user.has_perm('accounts.can_delete_repository')
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('start-indexing/', 
                 permission_required_custom('can_index_repository')(
                     self.admin_site.admin_view(self.start_indexing_view)
                 ), 
                 name='start_indexing'),
        ]
        return custom_urls + urls
    
    def start_indexing_view(self, request):
        # ... (Previous indexing code logic) ...
        pending_files = RepositoryFile.objects.filter(status='pending')
        
        if not pending_files.exists():
            messages.info(request, "Tidak ada file pending untuk diindeks.")
            return redirect('admin:repository_repositoryfile_changelist')

        for repo_file in pending_files:
            if request.session.get('cancel_indexing', False):
                messages.warning(request, "Proses indexing dihentikan pengguna.")
                request.session['cancel_indexing'] = False
                break

            try:
                full_path = repo_file.file.path
                extracted_text = ""

                if repo_file.filetype == 'pdf':
                    doc = fitz.open(full_path)
                    for page in doc:
                        extracted_text += page.get_text()
                elif repo_file.filetype == 'docx':
                    doc = docx.Document(full_path)
                    extracted_text = '\n'.join([p.text for p in doc.paragraphs])

                extracted_text = ''.join([i for i in extracted_text if ord(i) < 128])

                txt_filename = f"{repo_file.id}.content.txt"
                txt_path = os.path.join(settings.MEDIA_ROOT, 'extracted', txt_filename)
                os.makedirs(os.path.dirname(txt_path), exist_ok=True)
                
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(extracted_text)

                repo_file.extracted_text_path = txt_path
                repo_file.extracted_text_length = len(extracted_text)
                repo_file.size_bytes = os.path.getsize(full_path)
                repo_file.index_date = timezone.now()
                repo_file.status = 'indexed'
                repo_file.save()

            except Exception as e:
                repo_file.status = 'failed'
                repo_file.error_message = str(e)
                repo_file.save()

        messages.success(request, "Proses indexing selesai.")
        return redirect('admin:repository_repositoryfile_changelist')