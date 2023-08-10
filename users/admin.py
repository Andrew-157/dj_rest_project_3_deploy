from django.contrib import admin
from django.utils.html import format_html
from users.models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = [
        'username', 'email', 'date_joined',
        'is_superuser', 'is_active', 'is_staff', 'image_tag'
    ]
    list_filter = ['username', 'date_joined']
    search_fields = ['username']
    readonly_fields = ['image_tag']

    def image_tag(self, obj):
        if obj.is_superuser:
            return None
        return format_html(f'<img src="{obj.image.url}" width="100" height="100">')
    image_tag.short_description = "User's image"
