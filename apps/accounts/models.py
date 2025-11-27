from django.contrib.auth.models import AbstractUser, Group
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('superadmin', 'Super Admin'),
        ('staff', 'Staff'),
        ('mahasiswa', 'Mahasiswa'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='mahasiswa')
    upload_limit = models.IntegerField(default=5, help_text="Kuota upload per hari")
    
    class Meta:
        db_table = 'user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

class ProxyGroup(Group):
    class Meta:
        proxy = True
        verbose_name = 'Group'
        verbose_name_plural = 'Groups'