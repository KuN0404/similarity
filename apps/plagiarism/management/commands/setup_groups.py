from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from apps.accounts.models import User

class Command(BaseCommand):
    help = 'Setup initial groups and permissions'

    def handle(self, *args, **kwargs):
        # Define permissions per group
        groups_permissions = {
            'Super Admin': [
                'can_check_plagiarism',
                'can_check_plagiarism_paste',
                'can_download_report',
                'can_view_repository',
                'can_add_repository',
                'can_edit_repository',
                'can_delete_repository',
                'can_index_repository',
                'can_view_own_history',
                'can_view_all_history',
                'can_manage_users',
                'can_manage_groups',
                'can_change_settings',
            ],
            'Staff': [
                'can_check_plagiarism',
                'can_check_plagiarism_paste',
                'can_download_report',
                'can_view_repository',
                'can_add_repository',
                'can_edit_repository',
                'can_delete_repository',
                'can_index_repository',
                'can_view_own_history',
                'can_view_all_history',
            ],
            'Mahasiswa': [
                'can_check_plagiarism',
                'can_check_plagiarism_paste',
                'can_download_report',
                'can_view_own_history',
            ],
        }

        content_type = ContentType.objects.get_for_model(User)

        for group_name, perm_codenames in groups_permissions.items():
            group, created = Group.objects.get_or_create(name=group_name)
            
            for codename in perm_codenames:
                try:
                    permission = Permission.objects.get(
                        codename=codename,
                        content_type=content_type
                    )
                    group.permissions.add(permission)
                except Permission.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'Permission {codename} not found')
                    )
            
            action = 'Created' if created else 'Updated'
            self.stdout.write(
                self.style.SUCCESS(f'{action} group: {group_name}')
            )

        self.stdout.write(self.style.SUCCESS('Groups setup completed!'))