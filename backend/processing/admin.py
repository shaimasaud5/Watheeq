from django.contrib import admin
from .models import TranscriptChunk, ProcessingResult
from preprocessing.models import Transcript


class TranscriptChunkInline(admin.TabularInline):
    model = TranscriptChunk
    extra = 0
    readonly_fields = ("chunk_index", "short_chunk_text", "semantic_english_text", "embedding_preview", "status", "error_message")
    fields = ("chunk_index", "short_chunk_text", "semantic_english_text", "embedding_preview", "status", "error_message")
    can_delete = False
    show_change_link = True

    def short_chunk_text(self, obj):
        return obj.chunk_text[:80] + "..." if len(obj.chunk_text) > 80 else obj.chunk_text
    short_chunk_text.short_description = "Chunk Text"

    def embedding_preview(self, obj):
        if obj.embedding:
            preview = ", ".join(f"{x:.4f}" for x in obj.embedding[:3])
            return f" [{preview}, ...] "
        return " No embedding"
    embedding_preview.short_description = "Embedding"


class TranscriptWithChunksAdmin(admin.ModelAdmin):
    list_display = ("meeting", "status", "source", "created_at", "chunk_count")
    readonly_fields = ("ordered_processed_json", "created_at")
    fields = ("meeting", "status", "source", "meeting_link", "ordered_processed_json", "created_at")
    inlines = [TranscriptChunkInline]

    def chunk_count(self, obj):
        return obj.chunks.count()
    chunk_count.short_description = "Chunks"

    def ordered_processed_json(self, obj):
        from django.utils.html import format_html
        import json
        if not obj.processed_json:
            return "-"
        formatted = json.dumps(obj.processed_json, indent=2, ensure_ascii=False)
        return format_html("<pre style='white-space: pre-wrap;'>{}</pre>", formatted)
    ordered_processed_json.short_description = "Processed JSON"


@admin.register(ProcessingResult)
class ProcessingResultAdmin(admin.ModelAdmin):
    list_display = ("id", "transcript", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("transcript__meeting__project__name",)


admin.site.unregister(Transcript) if admin.site.is_registered(Transcript) else None
admin.site.register(Transcript, TranscriptWithChunksAdmin)