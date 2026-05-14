"""
Orchestrates the full pipeline:
  (audio) -> STT -> summarise -> translate -> TTS
  (text)         -> summarise -> translate -> TTS
"""
import os
import tempfile
import mimetypes
from typing import Optional, Tuple

# Audio duration check
SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".aac"}
MAX_AUDIO_DURATION_SECONDS = 5 * 60  # 5 minutes 


def check_audio_duration(audio_path: str) -> None:
    """
    Raises ValueError if the audio file exceeds MAX_AUDIO_DURATION_SECONDS.
    Uses mutagen for metadata-based duration check.
    """
    from mutagen import File as MutagenFile  # type: ignore
    audio = MutagenFile(audio_path)
    if audio is not None and audio.info is not None:
        duration = audio.info.length
        if duration > MAX_AUDIO_DURATION_SECONDS:
            mins = int(duration // 60)
            secs = int(duration % 60)
            raise ValueError(
                f"Audio file is {mins}m {secs}s long, which exceeds the 5-minute limit. "
                "Please upload a shorter clip."
            )


def run_pipeline(
    input_text: Optional[str],
    audio_path: Optional[str],
    target_language: str,
) -> Tuple[str, str, str, bytes]:
    """
    Run the full pipeline and return:
        (transcript_or_source_text, summary, translated_summary, audio_bytes)

    Raises ValueError / requests.HTTPError on failures.
    """
    from backend.sunbird_client import (
        transcribe_audio,
        summarise_text,
        translate_text,
        synthesise_speech,
        detect_text_language,
        SUMMARISE_SUPPORTED_LANGUAGES,
    )

    # ── Step 1: get source text ──────────────────────────────────────────────
    if audio_path:
        ext = os.path.splitext(audio_path)[-1].lower()
        if ext not in SUPPORTED_AUDIO_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type '{ext or '(none)'}'. "
                f"Please upload one of: MP3, WAV, OGG, M4A, AAC."
            )
        check_audio_duration(audio_path)
        transcript = transcribe_audio(audio_path)
        source_text = transcript
    elif input_text and input_text.strip():
        transcript = input_text.strip()
        source_text = transcript
    else:
        raise ValueError("Please provide either text input or an audio file.")

    # ── Step 2: detect language, then summarise ──────────────────────────────
    detected_language = detect_text_language(source_text)
    if detected_language not in SUMMARISE_SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Your input was detected as '{detected_language}' — summarisation only supports "
            f"English (eng) and Luganda (lug). Please provide input in one of those languages."
        )
    summary = summarise_text(source_text, language_code=detected_language)

    # ── Step 3: translate ────────────────────────────────────────────────────
    translation = translate_text(summary, target_language)

    # ── Step 4: TTS ──────────────────────────────────────────────────────────
    audio_bytes = synthesise_speech(translation, target_language)

    return transcript, summary, translation, audio_bytes