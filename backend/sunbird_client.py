"""
Thin wrapper around Sunbird AI API endpoints (robust version).
"""
import os
import requests
from typing import Optional

SUNBIRD_API_BASE = "https://api.sunbird.ai"

# TTS speaker IDs per language
TTS_SPEAKER_IDS = {
    "Acholi": 241,
    "Ateso": 242,
    "Runyankole": 243,
    "Lugbara": 245,
    "Luganda": 248,
}

STT_LANGUAGE_CODES = {
    "Acholi": "ach",
    "Ateso": "teo",
    "English": "eng",
    "Luganda": "lug",
    "Lugbara": "lgg",
    "Runyankole": "nyn",
}

LANGUAGE_NAMES = {
    "Acholi": "Acholi",
    "Ateso": "Ateso",
    "Runyankole": "Runyankole",
    "Lugbara": "Lugbara",
    "Luganda": "Luganda",
}

# Languages supported by the summarisation endpoint
SUMMARISE_SUPPORTED_LANGUAGES = {"eng", "lug"}

# -----------------------------
# Helpers
# -----------------------------
def _get_headers(content_type: Optional[str] = None) -> dict:
    token = os.environ.get("SUNBIRD_API_TOKEN")
    if not token:
        raise ValueError("SUNBIRD_API_TOKEN is not set in environment variables.")

    headers = {"Authorization": f"Bearer {token}"}
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def _extract(data: dict, *keys):
    """
    Robust extractor for Sunbird API inconsistencies.
    Never assumes presence of 'output'.
    """

    if not isinstance(data, dict):
        raise Exception(f"Invalid API response: {data}")

    # ----------------------------
    # Case 1: output wrapper exists
    # ----------------------------
    if isinstance(data.get("output"), dict):
        inner = data["output"]

        for k in keys:
            if k in inner:
                return inner[k]

        # fallback: sometimes content is nested differently
        if "content" in inner:
            return inner["content"]
        if "text" in inner:
            return inner["text"]

    # ----------------------------
    # Case 2: flat response
    # ----------------------------
    for k in keys:
        if k in data:
            return data[k]

    # ----------------------------
    # Case 3: known Sunbird variations
    # ----------------------------
    if "content" in data:
        return data["content"]
    if "text" in data:
        return data["text"]
    if "summary" in data:
        return data["summary"]
    if "summarized_text" in data:
        return data["summarized_text"]
    if "audio_transcription" in data:
        return data["audio_transcription"]

    # last resort debugging
    raise Exception(f"Unexpected API response format: {data}")


# -----------------------------
# LANGUAGE DETECTION
# -----------------------------
def detect_text_language(text: str) -> str:
    """
    Returns the detected language code (e.g. 'eng', 'lug') for a text string.
    Uses /tasks/language_id endpoint.
    """
    url = f"{SUNBIRD_API_BASE}/tasks/language_id"
    headers = _get_headers("application/json")
    payload = {"text": text}

    response = requests.post(url, json=payload, headers=headers, timeout=(30, 60))
    response.raise_for_status()

    data = response.json()
    return _extract(data, "language")


def detect_audio_language(audio_path: str) -> str:
    """
    Returns the detected language code (e.g. 'ach', 'lug') for an audio file.
    Uses /tasks/auto_detect_audio_language endpoint.
    """
    url = f"{SUNBIRD_API_BASE}/tasks/auto_detect_audio_language"
    headers = _get_headers()

    with open(audio_path, "rb") as f:
        files = {"audio": f}
        response = requests.post(url, files=files, headers=headers, timeout=(10, 120))

    response.raise_for_status()
    data = response.json()
    return _extract(data, "language")


# -----------------------------
# STT
# -----------------------------
def transcribe_audio(audio_path: str) -> str:
    url = f"{SUNBIRD_API_BASE}/tasks/stt"
    headers = _get_headers()

    import mimetypes
    ext = os.path.splitext(audio_path)[-1].lower() or ".wav"
    mime = mimetypes.types_map.get(ext, "audio/wav")
    filename = f"audio{ext}"

    with open(audio_path, "rb") as f:
        files = {"audio": (filename, f, mime)}
        response = requests.post(url, files=files, headers=headers, timeout=(20, 300))

    response.raise_for_status()
    data = response.json()

    return _extract(data, "audio_transcription", "text")


# -----------------------------
# SUMMARISATION
# -----------------------------
def summarise_text(text: str, language_code: str = "eng") -> str:
    if language_code not in SUMMARISE_SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Summarisation only supports English (eng) and Luganda (lug), "
            f"but received '{language_code}'. Please provide input text in English or Luganda."
        )
    url = f"{SUNBIRD_API_BASE}/tasks/summarise"
    headers = _get_headers("application/json")
    payload = {"text": text}

    response = requests.post(url, json=payload, headers=headers, timeout=(10, 300))
    response.raise_for_status()

    data = response.json()

    return _extract(data, "summary", "summarized_text")


# -----------------------------
# TRANSLATION
# -----------------------------
def translate_text(text: str, target_language: str) -> str:
    url = f"{SUNBIRD_API_BASE}/tasks/sunflower_inference"
    headers = _get_headers("application/json")

    lang_name = LANGUAGE_NAMES.get(target_language, target_language)

    payload = {
        "messages": [
            {
                "role": "system",
                "content": (
                    f"You are a professional translator for Ugandan languages. "
                    f"Translate into {lang_name}. Return ONLY translation."
                ),
            },
            {
                "role": "user",
                "content": f"Translate into {lang_name}:\n\n{text}",
            },
        ]
    }

    response = requests.post(url, json=payload, headers=headers, timeout=(10, 300))
    response.raise_for_status()

    data = response.json()

    return _extract(data, "content", "text")


# -----------------------------
# TTS
# -----------------------------
def synthesise_speech(text: str, language: str) -> bytes:
    speaker_id = TTS_SPEAKER_IDS.get(language)
    if speaker_id is None:
        raise ValueError(f"No TTS speaker available for language: {language}")

    url = f"{SUNBIRD_API_BASE}/tasks/tts"
    headers = _get_headers("application/json")

    payload = {
        "text": text,
        "speaker_id": speaker_id
    }

    response = requests.post(url, json=payload, headers=headers, timeout=(10, 120))
    response.raise_for_status()

    data = response.json()

    audio_url = _extract(data, "audio_url")

    try:
        audio_response = requests.get(audio_url, timeout=(10, 120))
        audio_response.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "The speech audio was generated but could not be downloaded. "
            "Please check your internet connection and try again."
        )
    except requests.exceptions.Timeout:
        raise RuntimeError(
            "The audio download timed out. Please try again."
        )
    except requests.exceptions.HTTPError:
        raise RuntimeError(
            "The speech audio could not be retrieved from the server. Please try again."
        )

    return audio_response.content