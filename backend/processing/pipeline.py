from preprocessing.models import Transcript
from processing.models import TranscriptChunk
from processing.services import simple_chunk, convert_chunk_to_semantic_english, generate_embeddings


def run_processing_pipeline(transcript: Transcript):
    """
    Receives a Transcript object from the database and runs the full pipeline:
    1. Chunking
    2. Semantic English
    3. Embeddings
    4. Saves results to the database
    """

    transcript_data = transcript.processed_json
    meeting_id = transcript_data.get("meeting_id", "unknown")

    print(f"\n{'='*60}")
    print(f"Starting pipeline for meeting: {meeting_id}")
    print(f"{'='*60}")

    # Step 1: Chunking
    print(f"\n[ STEP 1 ] Chunking...")
    chunks = simple_chunk(transcript_data, max_chars=300, overlap_lines=1)
    print(f"  Total chunks: {len(chunks)}")

    if not chunks:
        print("  ERROR: No chunks produced.")
        return

    # Step 2: Semantic English
    print(f"\n[ STEP 2 ] Semantic English...")
    semantic_results = []

    # Save the last translated line from the previous chunk
    previous_last_translated_lines = []
    overlap_count = 1  # Same overlap used in chunking

    for i, chunk_text in enumerate(chunks):
        chunk_obj = TranscriptChunk.objects.create(
            transcript=transcript,
            chunk_index=i,
            chunk_text=chunk_text,
            status=TranscriptChunk.StatusChoices.PENDING
        )

        try:
            if i == 0:
                # First chunk is translated fully because there is no previous overlap
                semantic_text, model, duration = convert_chunk_to_semantic_english(chunk_text)

            else:
                # Split the chunk into the overlap line and the new lines
                lines = chunk_text.split("\n")
                new_lines = lines[overlap_count:]

                if new_lines:
                    # Translate only the new part of the chunk
                    translated_new_part, model, duration = convert_chunk_to_semantic_english(
                        "\n".join(new_lines)
                    )

                    # Combine the reused translated overlap with the new translation
                    semantic_text = "\n".join(
                        previous_last_translated_lines + [translated_new_part]
                    )
                else:
                    # If the chunk contains only overlap, reuse the previous translation
                    semantic_text = "\n".join(previous_last_translated_lines)
                    model = None
                    duration = None

            semantic_results.append(semantic_text)
            chunk_obj.semantic_english_text = semantic_text
            chunk_obj.save()

            # Store the last translated line to reuse it in the next chunk
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
            chunk_obj.save()

            print(f"  Chunk {i+1} FAILED: {e}")
            semantic_results.append("")

    # Step 3: Embeddings
    print(f"\n[ STEP 3 ] Embeddings...")
    valid_texts = [text for text in semantic_results if text]

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
                chunk_obj.save()
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
    print(f"Pipeline completed!")
    print(f"  Total chunks : {len(chunks)}")
    print(f"  Completed    : {completed}")
    print(f"  Failed       : {failed}")
    print(f"{'='*60}\n")