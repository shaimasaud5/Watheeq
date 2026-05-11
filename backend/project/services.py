import requests
from django.conf import settings
from .models import Meeting

def request_recall_bot(meeting_id: int) -> str:
    """
    Sends a request to Recall.ai to join the meeting.
    Recall.ai will send their bot to listen silently,
    and return the full transcript when the meeting ends.
    Saves the recall_bot_id in the Meeting record for later use in the webhook.
    """
    # 1. Get the meeting from the database
    meeting = Meeting.objects.get(id=meeting_id)

    # 2. Set up the request headers with our Recall.ai API key
    headers = {
        "Authorization": f"Token {settings.RECALL_API_KEY}",
        "Content-Type": "application/json",
    }

    # 3. Build the request body
    payload = {
        "meeting_url": meeting.meeting_link,
        "bot_name": "Watheeq Agent",
        
    }

    # 4. Send the request to Recall.ai
    response = requests.post(
        "https://ap-northeast-1.recall.ai/api/v1/bot/",
        headers=headers,
        json=payload,
    )

    # 5. If the request failed, raise an error
    if response.status_code != 201:
        raise Exception(f"Recall.ai error: {response.text}")

    # 6. Get the bot ID from the response
    recall_bot_id = response.json().get("id")

    # 7. Save the bot ID in the database so we can identify
    #    which meeting this transcript belongs to when the webhook is called
    meeting.recall_bot_id = recall_bot_id
    meeting.save(update_fields=["recall_bot_id"])

    return recall_bot_id