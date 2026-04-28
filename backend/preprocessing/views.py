import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .services import process_recording_done_webhook


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
        if event == "recording.done":
            process_recording_done_webhook(bot_id)

        else:
            print(f"Ignoring event: {event}")
            return JsonResponse({"status": "ignored"}, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"status": "ok"}, status=200)