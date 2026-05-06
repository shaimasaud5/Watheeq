from django.contrib import admin
from .models import Extraction


@admin.register(Extraction)
class ExtractionAdmin(admin.ModelAdmin):
    list_display = ["id", "document", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["document__project__name", "document__doc_type"]