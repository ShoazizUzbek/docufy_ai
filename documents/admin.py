from django.contrib import admin

from .models import Chunk, Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'organization', 'status', 'file_type', 'uploaded_by', 'created_at')
    list_filter = ('status', 'file_type', 'organization')
    search_fields = ('original_filename',)


@admin.register(Chunk)
class ChunkAdmin(admin.ModelAdmin):
    list_display = ('document', 'index', 'page_number', 'section_heading', 'token_count')
    list_filter = ('document__organization',)
    search_fields = ('text', 'section_heading', 'hierarchy_path')
    raw_id_fields = ('document',)
