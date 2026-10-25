"""Voice module: Text-to-speech (TTS) & Speech-to-text (STT).
Supports ElevenLabs if credentials are provided with intelligent SHA-256
audio caching to PROTECT user credits from redundant API calls,
and native macOS speech synthesis fallback (Soumya for kn, Lekha for hi, Rishi for en).
Returns a public URL under /media or None if audio cannot be generated.
"""
import hashlib
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

    # Clean text for speech and cap length to preserve API credits
    clean_text = text.replace("*", "").replace("_", "").replace("₹", "Rupees ").strip()
    # Credit protection: strictly cap summary to 280 characters maximum
    if len(clean_text) > 280:
        clean_text = clean_text[:277] + "..."

    # -------------------------------------------------------------
    # CREDIT SAFETY: Check SHA-256 Disk Cache First
    # Never spend ElevenLabs credits if the audio was already synthesized!
    # -------------------------------------------------------------
    cache_key = hashlib.sha256(f"{lang}:{clean_text}".encode()).hexdigest()[:16]
    cached_file = config.MEDIA_DIR / f"voice_cache_{cache_key}.mp3"
    if cached_file.exists() and cached_file.stat().st_size > 1024:
        print(f"[voice credit protection] Using cached audio for key {cache_key} (0 ElevenLabs credits used)")
        return f"{config.BASE_URL}/media/{cached_file.name}"

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
                cached_file.write_bytes(r.content)
                print(f"[elevenlabs tts] Synthesized and cached new audio: {cached_file.name}")
                return f"{config.BASE_URL}/media/{cached_file.name}"
            else:
                print(f"[elevenlabs tts response {r.status_code}] {r.text[:200]}")
        except Exception as e:
            print(f"[elevenlabs tts failed, trying native speech] {e}")

    # 2. Native macOS speech synthesis fallback (offline, zero-latency, 100% free)
    try:
        aiff_path = config.MEDIA_DIR / f"temp_{cache_key}.aiff"
        m4a_name = f"voice_cache_{cache_key}.m4a"
        m4a_path = config.MEDIA_DIR / m4a_name

        if m4a_path.exists() and m4a_path.stat().st_size > 1024:
            return f"{config.BASE_URL}/media/{m4a_name}"

        voice_name = VOICE_MAP.get(lang, "Rishi")

        # Pick language-appropriate voice: Soumya (kn), Lekha (hi), Rishi (en)
        subprocess.run(
            ["say", "-v", voice_name, "-o", str(aiff_path), clean_text],
            check=True,
            timeout=15,
        )
        # Convert AIFF to compressed M4A (AAC) suitable for inline playback
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
