import os
import django
import requests

print("Starting script...")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.conf import settings

bot_id = "9e52a093-c7d2-418a-bc21-5a299a9ccfb9"

headers = {
    "Authorization": f"Token {settings.RECALL_API_KEY}",
    "Accept": "application/json",
}

print("Fetching bot data...")

response = requests.get(
    f"https://ap-northeast-1.recall.ai/api/v1/bot/{bot_id}/",
    headers=headers,
    timeout=30,
)

print("Bot status:", response.status_code)
response.raise_for_status()

data = response.json()

print("Checking recordings...")
print("Recordings count:", len(data.get("recordings", [])))

recording = data["recordings"][0]
video_url = recording["media_shortcuts"]["video_mixed"]["data"]["download_url"]

print("Video URL found")

video_response = requests.get(video_url, timeout=120)
print("Download status:", video_response.status_code)
video_response.raise_for_status()

output_file = "/app/recall_test_video.mp4"
with open(output_file, "wb") as f:
    f.write(video_response.content)

print("Saved file:", output_file)
print("File size:", os.path.getsize(output_file), "bytes")