from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages

def permission_required_custom(permission_codename):
    """
    Custom permission decorator untuk replace role checking
    
    Usage:
        @permission_required_custom('can_check_plagiarism')
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if request.user.has_perm(f'accounts.{permission_codename}'):
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, "Anda tidak memiliki izin untuk mengakses halaman ini.")
                return redirect('admin:index')
        return _wrapped_view
    return decorator

def superadmin_required(view_func):
    """Shortcut untuk Super Admin only"""
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.user.groups.filter(name='Super Admin').exists() or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        messages.error(request, "Akses ditolak. Hanya Super Admin yang diizinkan.")
        return redirect('admin:index')
    return _wrapped_view