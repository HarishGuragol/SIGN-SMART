"""Text-to-speech via ElevenLabs. Returns a URL under /media, or None if voice
isn't configured or the call fails — callers treat voice as optional and
never let it block the chat (see states.run_report)."""
import secrets

import httpx

from . import config


def tts(text):
    if not config.ELEVENLABS_API_KEY or not config.ELEVENLABS_VOICE_ID or not text.strip():
        return None
    try:
        r = httpx.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{config.ELEVENLABS_VOICE_ID}",
            headers={"xi-api-key": config.ELEVENLABS_API_KEY, "accept": "audio/mpeg"},
            json={"text": text, "model_id": config.ELEVENLABS_MODEL,
                  "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}},
            timeout=60,
        )
        r.raise_for_status()
        name = f"voice_{secrets.token_hex(8)}.mp3"
        (config.MEDIA_DIR / name).write_bytes(r.content)
        return f"{config.BASE_URL}/media/{name}"
    except Exception as e:
        print(f"[voice tts failed] {e}")
        return None
