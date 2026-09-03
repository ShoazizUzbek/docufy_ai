from django.contrib import admin

from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'organization', 'status', 'file_type', 'uploaded_by', 'created_at')
    list_filter = ('status', 'file_type', 'organization')
    search_fields = ('original_filename',)
