from django.urls import path
from .views import recall_webhook

urlpatterns = [
    # Webhook endpoint called by Recall.ai when the meeting ends
    # POST /api/transcript/webhook/
    path("preprocessing/webhook/", recall_webhook),
]