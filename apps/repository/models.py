import uuid
import os
from django.db import models

def get_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    return f"documents/{instance.id}.{ext}"

class RepositoryFile(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Indexing'),
        ('indexed', 'Indexed'),
        ('failed', 'Indexing Failed'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    filename = models.CharField(max_length=255)
    basename = models.CharField(max_length=255, blank=True)
    filetype = models.CharField(max_length=10)
    
    # File asli
    file = models.FileField(upload_to=get_upload_path)
    
    # Path untuk hasil ekstraksi (.content.txt)
    extracted_text_path = models.CharField(max_length=500, blank=True, null=True)
    
    size_bytes = models.BigIntegerField(default=0)
    extracted_text_length = models.IntegerField(default=0)
    index_date = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, null=True)

    # Metadata Opsional
    title = models.CharField(max_length=255, blank=True)
    author = models.CharField(max_length=255, blank=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.filename:
            self.filename = os.path.basename(self.file.name)
        if not self.basename:
            self.basename = os.path.splitext(self.filename)[0]
        if not self.filetype:
            self.filetype = os.path.splitext(self.filename)[1].replace('.', '').lower()
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'repository_files'