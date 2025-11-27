from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'assigned_guide')
    list_filter = ('role', 'assigned_guide')
    fieldsets = UserAdmin.fieldsets + (
        ('Role & Assignment', {'fields': ('role', 'assigned_guide')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role & Assignment', {'fields': ('role', 'assigned_guide')}),
    )

# admin.site.register(CustomUser, CustomUserAdmin)
