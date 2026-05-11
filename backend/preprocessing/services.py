import os
import tempfile
import requests
from django.utils import timezone

from project.models import Meeting
from .models import Transcript
from .recall_media import fetch_recording_and_speakers
from .whisper_service import transcribe_audio
from .merge_speakers import build_processed_json_from_whisper_and_speakers


def download_recording(video_url: str) -> str:
    """
    Download recording temporarily inside the container.
    Returns the local file path.
    """

    response = requests.get(video_url, timeout=300)
    response.raise_for_status()

    temp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".mp4",
        dir="/tmp"
    )

    temp_file.write(response.content)
    temp_file.close()

    return temp_file.name


def process_recording_done_webhook(bot_id: str):
    """
    Main preprocessing flow:
    Recall recording + speakers
    → download recording
    → Faster Whisper transcription
    → merge speakers
    → save processed_json
    → delete recording

    Bar 2 status:
    pending → in_progress → completed / failed
    """

    meeting = Meeting.objects.get(recall_bot_id=bot_id)

    transcript, _ = Transcript.objects.update_or_create(
        meeting=meeting,
        defaults={
            "source": Transcript.SOURCE_HYBRID,
            "meeting_link": meeting.meeting_link,
            "status": Transcript.STATUS_IN_PROGRESS,
            "error_message": "",
        }
    )

    video_path = None

    try:
        video_url, speaker_timeline = fetch_recording_and_speakers(bot_id)

        video_path = download_recording(video_url)

        whisper_segments = transcribe_audio(video_path)

        # Only the general meeting status for Bar 1 is updated here
        meeting.status = Meeting.STATUS_TRANSCRIBED
        meeting.save(update_fields=["status"])

        processed_json = build_processed_json_from_whisper_and_speakers(
            whisper_segments=whisper_segments,
            speaker_timeline=speaker_timeline,
            meeting_id=meeting.id,
        )

        transcript.source = Transcript.SOURCE_HYBRID
        transcript.meeting_link = meeting.meeting_link
        transcript.processed_json = processed_json
        transcript.processed_at = timezone.now()
        # Update Bar 2 Task 1 to completed = JSON file received = text cleaned
        transcript.status = Transcript.STATUS_COMPLETED
        transcript.error_message = ""
        transcript.save(update_fields=[
            "source",
            "meeting_link",
            "processed_json",
            "processed_at",
            "status",
            "error_message",
        ])

        return processed_json

    except Exception as e:
        transcript.status = Transcript.STATUS_FAILED
        transcript.error_message = str(e)
        transcript.save(update_fields=["status", "error_message"])

        raise

    finally:
        if video_path and os.path.exists(video_path):
            os.remove(video_path)