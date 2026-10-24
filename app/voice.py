"""Text-to-speech module.
Supports ElevenLabs if credentials are provided, with an instant,
high-quality native macOS fallback (say -v Rishi / Tara + afconvert).
Returns a public URL under /media or None if audio cannot be generated.
"""
import secrets
import subprocess
from pathlib import Path

import httpx

from . import config


"""Voice module: Text-to-speech (TTS) & Speech-to-text (STT).
Supports ElevenLabs if credentials are provided (with auto-fallback to multilingual voice),
and native macOS speech synthesis fallback (Soumya for kn, Lekha for hi, Rishi for en).
Returns a public URL under /media or None if audio cannot be generated.
"""
import secrets
import subprocess
from pathlib import Path

import httpx

from . import config

VOICE_MAP = {
    "kn": "Soumya",
    "hi": "Lekha",
    "en": "Rishi",
}

DEFAULT_ELEVENLABS_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel / Multilingual


def tts(text: str, lang: str = "en") -> str | None:
    if not text or not text.strip():
        return None

    # Clean text for speech
    clean_text = text.replace("*", "").replace("_", "").replace("₹", "Rupees ")

    # 1. Try ElevenLabs if API key is provided
    if config.ELEVENLABS_API_KEY:
        voice_id = config.ELEVENLABS_VOICE_ID or DEFAULT_ELEVENLABS_VOICE_ID
        model_id = config.ELEVENLABS_MODEL or "eleven_multilingual_v2"
        try:
            r = httpx.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={"xi-api-key": config.ELEVENLABS_API_KEY, "accept": "audio/mpeg"},
                json={
                    "text": clean_text,
                    "model_id": model_id,
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
                },
                timeout=30,
            )
            if r.status_code == 200 and r.content:
                name = f"voice_{secrets.token_hex(8)}.mp3"
                (config.MEDIA_DIR / name).write_bytes(r.content)
                return f"{config.BASE_URL}/media/{name}"
            else:
                print(f"[elevenlabs tts response {r.status_code}] {r.text[:200]}")
        except Exception as e:
            print(f"[elevenlabs tts failed, trying native speech] {e}")

    # 2. Native macOS speech synthesis fallback (offline, zero-latency, language-matched voice)
    try:
        token = secrets.token_hex(8)
        aiff_path = config.MEDIA_DIR / f"temp_{token}.aiff"
        m4a_name = f"voice_{token}.m4a"
        m4a_path = config.MEDIA_DIR / m4a_name

        voice_name = VOICE_MAP.get(lang, "Rishi")

        # Pick language-appropriate voice: Soumya (kn), Lekha (hi), Rishi (en)
        subprocess.run(
            ["say", "-v", voice_name, "-o", str(aiff_path), clean_text],
            check=True,
            timeout=15,
        )
        # Convert AIFF to compressed M4A (AAC) suitable for Telegram inline playback
        subprocess.run(
            ["afconvert", str(aiff_path), str(m4a_path), "-d", "aac", "-f", "m4af"],
            check=True,
            timeout=10,
        )
        if aiff_path.exists():
            aiff_path.unlink()

        return f"{config.BASE_URL}/media/{m4a_name}"
    except Exception as e:
        print(f"[native speech synthesis failed] {e}")
        return None


def stt(audio_bytes: bytes, mime: str = "audio/ogg") -> str | None:
    """Speech-to-text using ElevenLabs Scribe or Whisper."""
    if not audio_bytes:
        return None

    if config.ELEVENLABS_API_KEY:
        try:
            files = {"file": ("audio.ogg", audio_bytes, mime or "audio/ogg")}
            data = {"model_id": "scribe_v1"}
            r = httpx.post(
                "https://api.elevenlabs.io/v1/speech-to-text",
                headers={"xi-api-key": config.ELEVENLABS_API_KEY},
                files=files,
                data=data,
                timeout=30,
            )
            if r.status_code == 200:
                txt = r.json().get("text", "").strip()
                if txt:
                    return txt
        except Exception as e:
            print(f"[elevenlabs stt failed] {e}")

    return None

