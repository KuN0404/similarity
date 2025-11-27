from django.contrib import admin
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import Group
from .models import User, ProxyGroup

# 1. Unregister Group bawaan (agar hilang dari menu 'Authentication')
try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass

# 2. Register User Custom
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Informasi Tambahan', {'fields': ('role', 'upload_limit')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informasi Tambahan', {'fields': ('role', 'upload_limit')}),
    )

# 3. Register Proxy Group (agar muncul di menu 'Accounts')
@admin.register(ProxyGroup)
class ProxyGroupAdmin(GroupAdmin):
    pass