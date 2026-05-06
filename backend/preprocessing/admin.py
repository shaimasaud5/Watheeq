from django.contrib import admin
from django.utils.html import format_html
import json
from .models import Transcript


@admin.register(Transcript)
class preprocessingAdmin(admin.ModelAdmin):
    """
    Admin view for Transcript model.
    Displays the processed JSON in a readable format.
    """

    list_display = ("meeting", "status", "source", "created_at")
    readonly_fields = ("ordered_processed_json", "created_at")
    fields = ("meeting", "status", "source", "meeting_link", "ordered_processed_json", "created_at")

    def ordered_processed_json(self, obj):
        """
        Display the processed JSON in a readable format.
        """
        if not obj.processed_json:
            return "-"

        ordered_data = {
            "meeting_id": obj.processed_json.get("meeting_id"),
            "turns": []
        }

        for turn in obj.processed_json.get("turns", []):
            ordered_data["turns"].append({
                "speaker": turn.get("speaker"),
                "start": turn.get("start"),
                "end": turn.get("end"),
                "text_raw": turn.get("text_raw"),
                "text_clean": turn.get("text_clean"),
            })

        formatted = json.dumps(ordered_data, indent=2, ensure_ascii=False)
        return format_html("<pre style='white-space: pre-wrap;'>{}</pre>", formatted)

    ordered_processed_json.short_description = "Processed JSON"