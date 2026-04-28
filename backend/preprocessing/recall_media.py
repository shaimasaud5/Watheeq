import requests
from django.conf import settings


def fetch_recording_and_speakers(bot_id: str):
    """
    Get recording video URL and speaker timeline data from Recall.
    """

    headers = {
        "Authorization": f"Token {settings.RECALL_API_KEY}",
        "Accept": "application/json",
    }

    # Get bot data from Recall
    response = requests.get(
        f"https://ap-northeast-1.recall.ai/api/v1/bot/{bot_id}/",
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()

    data = response.json()

    try:
        recording = data["recordings"][0]

        video_url = recording["media_shortcuts"]["video_mixed"]["data"]["download_url"]

        speaker_url = recording["media_shortcuts"]["participant_events"]["data"][
            "speaker_timeline_download_url"
        ]

    except (KeyError, IndexError, TypeError):
        raise Exception("Recording or speaker timeline not ready")

    # Download speaker timeline JSON directly
    speaker_response = requests.get(speaker_url, timeout=60)
    speaker_response.raise_for_status()

    speaker_timeline = speaker_response.json()

    return video_url, speaker_timeline