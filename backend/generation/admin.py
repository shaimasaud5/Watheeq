from django.contrib import admin
from .models import GeneratedDocument


@admin.register(GeneratedDocument)
class GeneratedDocumentAdmin(admin.ModelAdmin):
    list_display = ["id", "document", "status", "is_approved", "created_at"]
    readonly_fields = ["created_at"]
    list_filter = ["status", "is_approved"]
    search_fields = ["document__project__name", "document__doc_type"]