import json
import threading
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

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

    if event == "recording.done":
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

    else:
        print(f"Ignoring event: {event}")
        return JsonResponse({"status": "ignored"}, status=200)