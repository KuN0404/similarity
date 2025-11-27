from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

class User(AbstractUser):
    upload_limit = models.IntegerField(default=5, help_text="Kuota upload per hari")
    
    class Meta:
        db_table = 'user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        permissions = [
            # Plagiarism Check Permissions
            ('can_check_plagiarism', 'Can check plagiarism'),
            ('can_check_plagiarism_paste', 'Can check plagiarism via paste text'),
            ('can_download_report', 'Can download plagiarism report'),
            
            # Repository Permissions
            ('can_view_repository', 'Can view repository'),
            ('can_add_repository', 'Can add to repository'),
            ('can_edit_repository', 'Can edit repository'),
            ('can_delete_repository', 'Can delete from repository'),
            ('can_index_repository', 'Can run repository indexing'),
            
            # History Permissions
            ('can_view_own_history', 'Can view own history'),
            ('can_view_all_history', 'Can view all users history'),
            
            # User Management Permissions
            ('can_manage_users', 'Can manage users'),
            ('can_manage_groups', 'Can manage groups'),
            
            # Settings Permissions
            ('can_change_settings', 'Can change system settings'),
        ]
    
    @property
    def role_name(self):
        """Compatibility property untuk template yang masih pakai 'role'"""
        groups = self.groups.all()
        if groups.exists():
            return groups.first().name.lower()
        return 'mahasiswa'

# Signal untuk auto-assign group "Mahasiswa" saat user baru dibuat
@receiver(post_save, sender=User)
def assign_default_group(sender, instance, created, **kwargs):
    if created and not instance.is_superuser:
        mahasiswa_group, _ = Group.objects.get_or_create(name='Mahasiswa')
        instance.groups.add(mahasiswa_group)

class ProxyGroup(Group):
    class Meta:
        proxy = True
        verbose_name = 'Group'
        verbose_name_plural = 'Groups'