from django.db.models.signals import post_save
from django.dispatch import receiver

from processing.models import ProcessingResult, TranscriptChunk
from extract.models import Extraction


@receiver(post_save, sender=ProcessingResult)
def trigger_extraction(sender, instance, **kwargs):
    """
    Trigger extraction only after processing is completed.
    """

    if instance.status != ProcessingResult.STATUS_COMPLETED:
        return

    transcript = instance.transcript

    print(f"[ EXTRACT SIGNAL ] Processing completed for Transcript {transcript.id}, starting extraction...")

    try:
        chunks = list(
            TranscriptChunk.objects.filter(
                transcript=transcript,
                status=TranscriptChunk.StatusChoices.COMPLETED,
            ).order_by("chunk_index").values("semantic_english_text", "embedding")
        )

        if not chunks:
            print("[ EXTRACT ERROR ] No completed chunks found.")
            return

        first_chunk = TranscriptChunk.objects.filter(
            transcript=transcript,
            status=TranscriptChunk.StatusChoices.COMPLETED,
        ).first()

        from extract.extractor import extract_brd, extract_mom

        for document in transcript.meeting.project.documents.all():
            print(f"[ EXTRACT ] Starting {document.doc_type} extraction...")

            extraction, _ = Extraction.objects.update_or_create(
                document=document,
                defaults={
                    "chunk": first_chunk,
                    "filled_schema": {},
                    "status": Extraction.STATUS_IN_PROGRESS,
                    "error_message": "",
                }
            )

            try:
                if document.doc_type == "BRD":
                    filled_schema = extract_brd(chunks)
                elif document.doc_type == "MOM":
                    filled_schema = extract_mom(chunks)
                else:
                    raise Exception(f"Unsupported document type: {document.doc_type}")

                extraction.chunk = first_chunk
                extraction.filled_schema = filled_schema
                extraction.status = Extraction.STATUS_COMPLETED
                extraction.error_message = ""
                extraction.save(update_fields=[
                    "chunk",
                    "filled_schema",
                    "status",
                    "error_message",
                ])

                print(f"[ EXTRACT ] Done for document {document.id}")

            except Exception as e:
                extraction.status = Extraction.STATUS_FAILED
                extraction.error_message = str(e)
                extraction.save(update_fields=["status", "error_message"])

                print(f"[ EXTRACT ERROR ] Document {document.id}: {e}")

    except Exception as e:
        import traceback
        print(f"[ EXTRACT ERROR ] {e}")
        print(traceback.format_exc())