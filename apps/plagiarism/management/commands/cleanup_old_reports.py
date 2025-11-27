import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.history.models import PlagiarismHistory
from apps.plagiarism.models import PlagiarismSettings

class Command(BaseCommand):
    help = 'Hapus file laporan plagiarisme lama (record tetap ada)'

    def handle(self, *args, **options):
        auto_delete_days = PlagiarismSettings.get_auto_delete_days()
        
        if auto_delete_days <= 0:
            self.stdout.write(self.style.WARNING('Auto-delete dinonaktifkan (0 hari)'))
            return
        
        cutoff_date = timezone.now() - timedelta(days=auto_delete_days)
        
        # Ambil report yang completed dan belum dihapus filenya
        old_reports = PlagiarismHistory.objects.filter(
            completed_at__lt=cutoff_date,
            status='completed',
            file_deleted=False  # Hanya yang belum dihapus
        )
        
        count = 0
        for report in old_reports:
            # Delete file fisik SAJA
            if report.report_file and os.path.exists(report.report_file.path):
                try:
                    file_path = report.report_file.path
                    os.remove(file_path)
                    self.stdout.write(f'Deleted file: {file_path}')
                    
                    # Update record: tandai file sudah dihapus
                    report.file_deleted = True
                    report.file_deleted_at = timezone.now()
                    report.file_deleted_reason = f'Auto-cleanup after {auto_delete_days} days'
                    report.save()
                    
                    count += 1
                    self.stdout.write(f'✓ Marked as deleted: {report.filename}')
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error deleting file: {e}'))
        
        if count > 0:
            self.stdout.write(self.style.SUCCESS(f'✓ Berhasil menghapus {count} file laporan (>{auto_delete_days} hari)'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✓ Tidak ada file yang perlu dihapus'))