from django.db.models.signals import post_save
from django.dispatch import receiver
from preprocessing.models import Transcript
from .pipeline import run_processing_pipeline


@receiver(post_save, sender=Transcript)
def trigger_processing_pipeline(sender, instance, created, **kwargs):
    """
    Automatically triggers the processing pipeline
    when a new Transcript is saved to the database.
    """
    if created:
        print(f"[ SIGNAL ] New transcript detected, starting pipeline...")
        run_processing_pipeline(instance)
        