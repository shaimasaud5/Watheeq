import threading
from faster_whisper import WhisperModel
import os
from groq import Groq
'''   
_model = None
_lock = threading.Lock()

def get_whisper_model():
    global _model
    if _model is None:
        print("[WHISPER] Loading model...")
        _model = WhisperModel("large-v3", device="cpu", compute_type="int8")
        print("[WHISPER] Model loaded")
    return _model
'''
def transcribe_audio(audio_path: str) -> list:
    print(f"[WHISPER] Starting transcription for: {audio_path}")
    client = Groq(api_key=os.getenv("GROQ_API_KEY_TASK4"))
    
    with open(audio_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=f,
            model="whisper-large-v3",
            response_format="verbose_json",
        )
    
    results = []
    for i, segment in enumerate(transcription.segments, start=1):
        print(f"[WHISPER] Segment {i}: {segment['start']:.2f} -> {segment['end']:.2f}")
        results.append({
            "start": segment["start"],
            "end": segment["end"],
            "text": segment["text"].strip(),
        })

    print(f"[WHISPER] Done. Total segments: {len(results)}")
    return results