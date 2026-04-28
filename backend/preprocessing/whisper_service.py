from faster_whisper import WhisperModel


_model = None


def get_whisper_model():
    global _model

    if _model is None:
        print("[WHISPER] Loading model...")
        _model = WhisperModel("large-v3", device="cpu", compute_type="int8")
        print("[WHISPER] Model loaded")

    return _model


def transcribe_audio(audio_path: str) -> list:
    print(f"[WHISPER] Starting transcription for: {audio_path}")

    model = get_whisper_model()

    print("[WHISPER] Transcribing...")
    segments, info = model.transcribe(
        audio_path,
        task="transcribe",
        vad_filter=True,
        beam_size=5,
        temperature=0.0,
        condition_on_previous_text=False,
        no_speech_threshold=0.6,
        log_prob_threshold=-1.0,
        compression_ratio_threshold=2.4,
    )

    print(f"[WHISPER] Detected language: {info.language}")
    print(f"[WHISPER] Language probability: {info.language_probability}")

    results = []

    for i, segment in enumerate(segments, start=1):
        print(f"[WHISPER] Segment {i}: {segment.start:.2f} -> {segment.end:.2f}")
        results.append({
            "start": segment.start,
            "end": segment.end,
            "text": segment.text.strip(),
        })

    print(f"[WHISPER] Done. Total segments: {len(results)}")

    return results