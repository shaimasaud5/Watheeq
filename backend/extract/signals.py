from django.db.models.signals import post_save
from django.dispatch import receiver
from preprocessing.models import Transcript
from extract.models import Extraction
from processing.models import TranscriptChunk


@receiver(post_save, sender=Transcript)
def trigger_extraction(sender, instance, **kwargs):
    if instance.status != Transcript.STATUS_COMPLETED:
        return

    print(f"[ EXTRACT SIGNAL ] Transcript {instance.id} completed, starting extraction...")

    try:
        chunks = list(
            TranscriptChunk.objects.filter(
                transcript=instance,
                status=TranscriptChunk.StatusChoices.COMPLETED,
            ).order_by("chunk_index").values("semantic_english_text", "embedding")
        )

        for document in instance.meeting.project.documents.all():
            print(f"[ EXTRACT ] Starting {document.doc_type} extraction...")

            from extract.extractor import extract_brd, extract_mom
            if document.doc_type == "BRD":
                filled_schema = extract_brd(chunks)
            else:
                filled_schema = extract_mom(chunks)

            Extraction.objects.update_or_create(
                document=document,
                defaults={
                    "filled_schema": filled_schema,
                    "chunk": TranscriptChunk.objects.filter(
                        transcript=instance,
                        status=TranscriptChunk.StatusChoices.COMPLETED,
                    ).first(),
                }
            )
            print(f"[ EXTRACT ] Done for document {document.id}")

    except Exception as e:
        import traceback
        print(f"[ EXTRACT ERROR ] {e}")
        print(traceback.format_exc())
        