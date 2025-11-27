from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid

class PlagiarismHistory(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Menunggu'),
        ('processing', 'Sedang Diproses'),
        ('completed', 'Selesai'),
        ('failed', 'Gagal'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    filename = models.CharField(max_length=255)
    
    # Similarity scores (detailed)
    similarity_score = models.IntegerField(null=True, blank=True, help_text="Skor plagiarisme global (0-100)")
    similarity_local = models.IntegerField(null=True, blank=True, help_text="Skor dari repository lokal")
    similarity_internet = models.IntegerField(null=True, blank=True, help_text="Skor dari internet")
    
    # Detailed sources (JSON string - compatible dengan MariaDB TextField)
    matched_sources = models.TextField(null=True, blank=True, help_text="Detail sumber yang cocok (JSON string)")
    
    report_file = models.FileField(upload_to='reports/', null=True, blank=True)
    check_date = models.DateTimeField(auto_now_add=True)
    source_mode = models.CharField(max_length=20, choices=[
        ('local', 'Lokal'), 
        ('internet', 'Internet'), 
        ('both', 'Keduanya')
    ])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    progress = models.IntegerField(default=0)
    error_message = models.TextField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # File deletion tracking
    file_deleted = models.BooleanField(default=False)
    file_deleted_at = models.DateTimeField(null=True, blank=True)
    file_deleted_reason = models.CharField(max_length=100, null=True, blank=True, default='Auto-cleanup policy')
    
    class Meta:
        db_table = 'plagiarism_history'
        verbose_name = "Histori Pemeriksaan"
        verbose_name_plural = "Histori Pemeriksaan"
        ordering = ['-check_date']

    def __str__(self):
        return f"{self.filename} - {self.status} ({self.user.username})"
    
    def get_matched_sources(self):
        """
        Parse JSON matched sources dari TextField
        Returns dict dengan struktur: {'local': [...], 'internet': [...]}
        """
        if self.matched_sources:
            try:
                import json
                return json.loads(self.matched_sources)
            except (json.JSONDecodeError, TypeError, ValueError):
                return {'local': [], 'internet': []}
        return {'local': [], 'internet': []}
    
    def set_matched_sources(self, sources_dict):
        """
        Set matched sources sebagai JSON string
        Args:
            sources_dict: dict dengan struktur {'local': [...], 'internet': [...]}
        """
        import json
        self.matched_sources = json.dumps(sources_dict, ensure_ascii=False)


class UserUploadQuota(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    upload_count = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'user_upload_quota'
        unique_together = ('user', 'date')
        verbose_name = 'Kuota Upload User'
        verbose_name_plural = 'Kuota Upload User'
    
    @classmethod
    def check_quota(cls, user):
        today = timezone.now().date()
        quota, created = cls.objects.get_or_create(user=user, date=today, defaults={'upload_count': 0})
        return quota.upload_count < user.upload_limit
    
    @classmethod
    def increment_quota(cls, user, count=1):
        today = timezone.now().date()
        quota, created = cls.objects.get_or_create(user=user, date=today, defaults={'upload_count': 0})
        quota.upload_count += count
        quota.save()
        return quota.upload_count
    
    @classmethod
    def get_remaining_quota(cls, user):
        today = timezone.now().date()
        quota, created = cls.objects.get_or_create(user=user, date=today, defaults={'upload_count': 0})
        return max(0, user.upload_limit - quota.upload_count)