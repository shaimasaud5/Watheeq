from .cleaner import clean_arabic_text, LLMCleaner


# Convert seconds → HH:MM:SS format
def seconds_to_hhmmss(seconds: float) -> str:
    total_seconds = int(seconds)
    hh = total_seconds // 3600
    mm = (total_seconds % 3600) // 60
    ss = total_seconds % 60
    return f"{hh:02}:{mm:02}:{ss:02}"


# Calculate overlap between two time ranges
def calculate_overlap(start1: float, end1: float, start2: float, end2: float) -> float:
    return max(0, min(end1, end2) - max(start1, start2))


# Find the best speaker for a whisper segment based on overlap
def find_best_speaker(segment_start: float, segment_end: float, speaker_timeline: list) -> str:
    best_speaker = "Unknown"
    best_overlap = 0

    for item in speaker_timeline:

        # Skip entries with missing timestamps (Recall may return null values)
        if not item.get("start_timestamp") or not item.get("end_timestamp"):
            continue

        speaker_start = item["start_timestamp"]["relative"]
        speaker_end = item["end_timestamp"]["relative"]
        speaker_name = item.get("participant", {}).get("name", "Unknown")

        overlap = calculate_overlap(segment_start, segment_end, speaker_start, speaker_end)

        if overlap > best_overlap:
            best_overlap = overlap
            best_speaker = speaker_name

    return best_speaker


# Merge consecutive segments from the same speaker
def merge_consecutive_same_speaker(turns: list, gap_threshold: float = 1.0) -> list:
    if not turns:
        return []

    merged = [turns[0]]

    for current in turns[1:]:
        previous = merged[-1]

        same_speaker = current["speaker"] == previous["speaker"]
        gap = current["start_seconds"] - previous["end_seconds"]

        # If same speaker and small gap → merge
        if same_speaker and gap <= gap_threshold:
            previous["end_seconds"] = current["end_seconds"]
            previous["text_raw"] += " " + current["text_raw"]
        else:
            merged.append(current)

    return merged


# Build final processed_json from whisper + speakers
def build_processed_json_from_whisper_and_speakers(
    whisper_segments: list,
    speaker_timeline: list,
    meeting_id: int,
) -> dict:

    turns = []

    # Assign speaker to each whisper segment
    for segment in whisper_segments:
        speaker = find_best_speaker(
            segment_start=segment["start"],
            segment_end=segment["end"],
            speaker_timeline=speaker_timeline,
        )

        turns.append({
            "speaker": speaker,
            "start_seconds": segment["start"],
            "end_seconds": segment["end"],
            "text_raw": segment["text"],
        })

    # Merge same-speaker segments
    merged_turns = merge_consecutive_same_speaker(turns)

    cleaner = LLMCleaner()
    final_turns = []

    for turn in merged_turns:
        text_raw = turn["text_raw"]

        # Clean the raw Whisper text
        text_clean = cleaner.correct(clean_arabic_text(text_raw))

        final_turns.append({
            "speaker": turn["speaker"],
            "start": seconds_to_hhmmss(turn["start_seconds"]),
            "end": seconds_to_hhmmss(turn["end_seconds"]),
            "text_raw": text_raw,
            "text_clean": text_clean,
        })

    return {
        "meeting_id": str(meeting_id),
        "turns": final_turns,
    }