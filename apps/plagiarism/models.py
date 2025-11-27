from django.db import models

class PlagiarismSettings(models.Model):
    similarity_threshold = models.IntegerField(
        default=75, 
        help_text="Batas minimum kemiripan untuk dianggap plagiat (0-100)"
    )
    auto_delete_days = models.IntegerField(
        default=30,
        help_text="Hapus otomatis laporan setelah N hari (0 = tidak otomatis hapus)"
    )
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'plagiarism_settings'
        verbose_name = 'Pengaturan Plagiarisme'
        verbose_name_plural = 'Pengaturan Plagiarisme'
    
    def __str__(self):
        return f"Threshold: {self.similarity_threshold}% | Auto-delete: {self.auto_delete_days} hari"
    
    @classmethod
    def get_threshold(cls):
        settings, created = cls.objects.get_or_create(
            id=1,
            defaults={'similarity_threshold': 75, 'auto_delete_days': 30}
        )
        return settings.similarity_threshold
    
    @classmethod
    def get_auto_delete_days(cls):
        settings, created = cls.objects.get_or_create(
            id=1,
            defaults={'similarity_threshold': 75, 'auto_delete_days': 30}
        )
        return settings.auto_delete_days
    
    def save(self, *args, **kwargs):
        self.id = 1
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        pass