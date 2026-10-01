from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from simple_history.admin import SimpleHistoryAdmin

from .models import User


@admin.register(User)
class SigtransUserAdmin(UserAdmin, SimpleHistoryAdmin):
    list_display = ("username", "first_name", "last_name", "perfil", "is_active", "is_staff")
    list_filter = ("perfil", "is_active", "is_staff")
    fieldsets = UserAdmin.fieldsets + (
        ("SIGTRANS", {"fields": ("perfil", "telefone")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("SIGTRANS", {"fields": ("perfil", "telefone", "first_name", "last_name", "email")}),
    )
