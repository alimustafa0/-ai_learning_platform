from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


class CustomUserAdmin(UserAdmin):
    """Define admin model for custom User model with no username field."""
    
    # Fields to display in the list view
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_active')
    
    # Fields to filter by in the right sidebar
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    
    # Fieldsets for the edit page
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'bio', 'avatar', 'website', 'location')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    # Fieldsets for the add page
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', "is_staff", "is_active"),
        }),
    )
    
    # Search fields
    search_fields = ('email', 'first_name', 'last_name')
    
    # Default ordering
    ordering = ('email',)

# Register the custom User model with the custom admin class
admin.site.register(User, CustomUserAdmin)