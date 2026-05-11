from django.utils import timezone

from preprocessing.models import Transcript
from processing.models import TranscriptChunk, ProcessingResult
from processing.services import (
    simple_chunk,
    convert_chunk_to_semantic_english,
    generate_embeddings,
)


def run_processing_pipeline(transcript: Transcript):
    """
    Receives a Transcript object from the database and runs the full pipeline:
    1. Chunking
    2. Semantic English
    3. Embeddings
    4. Saves results to the database
    """

    processing_result, _ = ProcessingResult.objects.update_or_create(
        transcript=transcript,
        defaults={
            "status": ProcessingResult.STATUS_IN_PROGRESS,
            "error_message": "",
        }
    )

    try:
        transcript_data = transcript.processed_json or {}
        meeting_id = transcript_data.get("meeting_id", "unknown")

        print(f"\n{'='*60}")
        print(f"Starting processing pipeline for meeting: {meeting_id}")
        print(f"{'='*60}")

        # Step 1: Chunking
        print(f"\n[ STEP 1 ] Chunking...")
        chunks = simple_chunk(transcript_data, max_chars=300, overlap_lines=1)
        print(f"  Total chunks: {len(chunks)}")

        if not chunks:
            processing_result.status = ProcessingResult.STATUS_FAILED
            processing_result.error_message = "No chunks produced."
            processing_result.processed_at = timezone.now()
            processing_result.save(update_fields=[
                "status",
                "error_message",
                "processed_at",
            ])
            print("  ERROR: No chunks produced.")
            return

        # Prevent duplicate chunks if processing is re-run for the same transcript.
        TranscriptChunk.objects.filter(transcript=transcript).delete()

        # Step 2: Semantic English
        print(f"\n[ STEP 2 ] Semantic English...")
        semantic_results = []

        previous_last_translated_lines = []
        overlap_count = 1

        for i, chunk_text in enumerate(chunks):
            chunk_obj = TranscriptChunk.objects.create(
                transcript=transcript,
                chunk_index=i,
                chunk_text=chunk_text,
                status=TranscriptChunk.StatusChoices.PENDING
            )

            try:
                if i == 0:
                    semantic_text, model, duration = convert_chunk_to_semantic_english(chunk_text)

                else:
                    lines = chunk_text.split("\n")
                    new_lines = lines[overlap_count:] if len(lines) > overlap_count else lines

                    if new_lines:
                        translated_new_part, model, duration = convert_chunk_to_semantic_english(
                            "\n".join(new_lines)
                        )

                        semantic_text = "\n".join(
                            previous_last_translated_lines + [translated_new_part]
                        )
                    else:
                        semantic_text = "\n".join(previous_last_translated_lines)
                        model = None
                        duration = None

                semantic_results.append(semantic_text)
                chunk_obj.semantic_english_text = semantic_text
                chunk_obj.save(update_fields=["semantic_english_text"])

                translated_lines = semantic_text.split("\n")
                previous_last_translated_lines = translated_lines[-overlap_count:]

                print(
                    f"  Chunk {i+1}/{len(chunks)} done ({duration:.1f}s)"
                    if duration else
                    f"  Chunk {i+1}/{len(chunks)} done"
                )

            except Exception as e:
                chunk_obj.status = TranscriptChunk.StatusChoices.FAILED
                chunk_obj.error_message = str(e)
                chunk_obj.save(update_fields=["status", "error_message"])

                print(f"  Chunk {i+1} FAILED: {e}")
                semantic_results.append("")

        # Step 3: Embeddings
        print(f"\n[ STEP 3 ] Embeddings...")
        valid_texts = [text for text in semantic_results if text]

        if not valid_texts:
            raise Exception("No valid semantic English texts to generate embeddings.")

        try:
            embeddings, embed_model, embed_duration = generate_embeddings(valid_texts)
            print(f"  Embeddings: {len(embeddings)} vectors")

            embed_index = 0
            for i, chunk_text in enumerate(chunks):
                if semantic_results[i]:
                    chunk_obj = TranscriptChunk.objects.get(
                        transcript=transcript,
                        chunk_index=i
                    )
                    chunk_obj.embedding = embeddings[embed_index]
                    chunk_obj.status = TranscriptChunk.StatusChoices.COMPLETED
                    chunk_obj.save(update_fields=["embedding", "status"])
                    embed_index += 1

        except Exception as e:
            print(f"  Embeddings FAILED: {e}")

            TranscriptChunk.objects.filter(
                transcript=transcript,
                status=TranscriptChunk.StatusChoices.PENDING
            ).update(
                status=TranscriptChunk.StatusChoices.FAILED,
                error_message=str(e)
            )

            raise

        # Step 4: Summary
        completed = TranscriptChunk.objects.filter(
            transcript=transcript,
            status=TranscriptChunk.StatusChoices.COMPLETED
        ).count()

        failed = TranscriptChunk.objects.filter(
            transcript=transcript,
            status=TranscriptChunk.StatusChoices.FAILED
        ).count()

        print(f"\n{'='*60}")
        print(f"Processing pipeline completed!")
        print(f"  Total chunks : {len(chunks)}")
        print(f"  Completed    : {completed}")
        print(f"  Failed       : {failed}")
        print(f"{'='*60}\n")

        if completed > 0:
            processing_result.status = ProcessingResult.STATUS_COMPLETED
            processing_result.error_message = ""
        else:
            processing_result.status = ProcessingResult.STATUS_FAILED
            processing_result.error_message = "No chunks completed successfully."

        processing_result.processed_at = timezone.now()
        processing_result.save(update_fields=[
            "status",
            "error_message",
            "processed_at",
        ])

    except Exception as e:
        processing_result.status = ProcessingResult.STATUS_FAILED
        processing_result.error_message = str(e)
        processing_result.processed_at = timezone.now()
        processing_result.save(update_fields=[
            "status",
            "error_message",
            "processed_at",
        ])
        raise