from django.contrib import admin
from .models import Extraction

@admin.register(Extraction)
class ExtractionAdmin(admin.ModelAdmin):
    list_display  = ["id", "document", "created_at"]
    readonly_fields = ["filled_schema", "created_at"]
