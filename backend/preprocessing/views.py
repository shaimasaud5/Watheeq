import json
import threading
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from project.models import Meeting
from .services import process_recording_done_webhook

_processing_bots = set()


@csrf_exempt
@require_POST
def recall_webhook(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    event = data.get("event")
    print(f"Received event: {event}")

    bot_id = data.get("data", {}).get("bot", {}).get("id")
    if not bot_id:
        return JsonResponse({"error": "Missing bot_id"}, status=400)

    try:
        meeting = Meeting.objects.get(recall_bot_id=bot_id)
    except Meeting.DoesNotExist:
        return JsonResponse({"error": "Meeting not found"}, status=404)

    # BAR 1: update meeting status from Recall bot events
    if event == "bot.joining_call":
        meeting.status = Meeting.STATUS_JOINING
        meeting.save(update_fields=["status"])
        return JsonResponse({"status": "joining"}, status=200)

    if event == "bot.in_call_recording":
        meeting.status = Meeting.STATUS_IN_MEETING
        meeting.save(update_fields=["status"])
        return JsonResponse({"status": "in_meeting"}, status=200)

    if event == "bot.call_ended":
        meeting.status = Meeting.STATUS_ENDED
        meeting.save(update_fields=["status"])
        return JsonResponse({"status": "ended"}, status=200)

    if event == "recording.done":
        meeting.status = Meeting.STATUS_POST_MEETING
        meeting.save(update_fields=["status"])

        if bot_id in _processing_bots:
            print(f"[WEBHOOK] Already processing: {bot_id}")
            return JsonResponse({"status": "already_processing"}, status=200)

        _processing_bots.add(bot_id)

        def run_and_cleanup():
            try:
                process_recording_done_webhook(bot_id)
            except Exception as e:
                import traceback
                print(f"[WEBHOOK ERROR] {e}")
                print(traceback.format_exc())
            finally:
                _processing_bots.discard(bot_id)

        thread = threading.Thread(target=run_and_cleanup, daemon=True)
        thread.start()
        return JsonResponse({"status": "processing"}, status=200)

    print(f"Ignoring event: {event}")
    return JsonResponse({"status": "ignored"}, status=200)