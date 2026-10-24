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


def tts(text: str) -> str | None:
    if not text or not text.strip():
        return None

    # 1. Try ElevenLabs if configured
    if config.ELEVENLABS_API_KEY and config.ELEVENLABS_VOICE_ID:
        try:
            r = httpx.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{config.ELEVENLABS_VOICE_ID}",
                headers={"xi-api-key": config.ELEVENLABS_API_KEY, "accept": "audio/mpeg"},
                json={
                    "text": text,
                    "model_id": config.ELEVENLABS_MODEL,
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
                },
                timeout=30,
            )
            r.raise_for_status()
            name = f"voice_{secrets.token_hex(8)}.mp3"
            (config.MEDIA_DIR / name).write_bytes(r.content)
            return f"{config.BASE_URL}/media/{name}"
        except Exception as e:
            print(f"[elevenlabs tts failed, trying native speech] {e}")

    # 2. Native macOS speech synthesis fallback (offline, zero-latency, realistic en_IN voice)
    try:
        token = secrets.token_hex(8)
        aiff_path = config.MEDIA_DIR / f"temp_{token}.aiff"
        m4a_name = f"voice_{token}.m4a"
        m4a_path = config.MEDIA_DIR / m4a_name

        # Clean text for speech
        clean_text = text.replace("*", "").replace("_", "").replace("₹", "Rupees ")

        # Pick voice: Rishi (en_IN male), Tara (en_IN female), or default
        subprocess.run(
            ["say", "-v", "Rishi", "-o", str(aiff_path), clean_text],
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
