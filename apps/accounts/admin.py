from django.contrib import admin
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import Group
from .models import User, ProxyGroup

try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'get_groups', 'is_staff', 'is_active')
    list_filter = ('groups', 'is_staff', 'is_active')
    
    fieldsets = UserAdmin.fieldsets + (
        ('Informasi Tambahan', {
            'fields': ('upload_limit',)
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informasi Tambahan', {
            'fields': ('upload_limit',)
        }),
    )
    
    filter_horizontal = ('groups', 'user_permissions')
    
    def get_groups(self, obj):
        return ", ".join([g.name for g in obj.groups.all()])
    get_groups.short_description = 'Groups/Roles'

@admin.register(ProxyGroup)
class ProxyGroupAdmin(GroupAdmin):
    pass