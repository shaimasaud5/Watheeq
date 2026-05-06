from django.db.models.signals import post_save
from django.dispatch import receiver
from preprocessing.models import Transcript
from .pipeline import run_processing_pipeline


@receiver(post_save, sender=Transcript)
def trigger_processing_pipeline(sender, instance, created, **kwargs):

    if (
        instance.status == Transcript.STATUS_COMPLETED
        and not hasattr(instance, "processing_result")
    ):
        print("[ SIGNAL ] Preprocessing completed, starting processing pipeline...")
        run_processing_pipeline(instance)