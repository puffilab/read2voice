import json
import time
from typing import Literal

import httpx

try:
    import edge_tts
except Exception:
    edge_tts = None


EngineType = Literal["openai", "edge_tts", "custom_http"]
_EDGE_VOICES_CACHE: dict | None = None
_EDGE_VOICES_CACHE_AT = 0.0
_EDGE_VOICES_CACHE_TTL_SECONDS = 3600
DEFAULT_EDGE_VOICE = "zh-CN-XiaoxiaoNeural"


OPENAI_VOICES = [
    "alloy",
    "ash",
    "ballad",
    "coral",
    "echo",
    "fable",
    "nova",
    "onyx",
    "sage",
    "shimmer",
]


def output_content_type(output_format: str) -> str:
    fmt = output_format.lower()
    if fmt == "mp3":
        return "audio/mpeg"
    if fmt == "wav":
        return "audio/wav"
    if fmt == "opus":
        return "audio/ogg"
    if fmt == "flac":
        return "audio/flac"
    if fmt == "pcm":
        return "audio/L16"
    return "application/octet-stream"


async def synthesize_openai(
    text: str,
    *,
    api_key: str,
    model: str,
    voice: str,
    output_format: str,
    speed: float,
    endpoint: str | None = None,
    instructions: str | None = None,
    timeout_seconds: int = 120,
) -> bytes:
    if not api_key:
        raise ValueError("OpenAI engine requires api_key")

    url = endpoint or "https://api.openai.com/v1/audio/speech"
    payload: dict = {
        "model": model or "gpt-4o-mini-tts",
        "voice": voice or "alloy",
        "input": text,
        "response_format": output_format or "mp3",
    }
    if instructions:
        payload["instructions"] = instructions
    if speed:
        payload["speed"] = speed

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        resp = await client.post(url, headers=headers, json=payload)
    if resp.status_code >= 400:
        detail = resp.text[:1000]
        raise RuntimeError(f"OpenAI API error {resp.status_code}: {detail}")
    return resp.content


async def synthesize_edge_tts(
    text: str,
    *,
    voice: str,
    speed: float,
) -> bytes:
    if edge_tts is None:
        raise RuntimeError("edge-tts is not installed")

    async def _run_once(voice_name: str) -> bytes:
        rate_percent = int(round((speed - 1.0) * 100))
        rate_text = f"{rate_percent:+d}%"
        comm = edge_tts.Communicate(text=text, voice=voice_name, rate=rate_text)
        audio = bytearray()
        async for chunk in comm.stream():
            if chunk.get("type") == "audio":
                audio.extend(chunk["data"])
        if not audio:
            raise RuntimeError("Edge TTS returned empty audio data")
        return bytes(audio)

    voice_name = (voice or "").strip() or DEFAULT_EDGE_VOICE
    try:
        return await _run_once(voice_name)
    except Exception as first_error:
        if voice_name == DEFAULT_EDGE_VOICE:
            raise first_error
        return await _run_once(DEFAULT_EDGE_VOICE)


async def list_engine_voices(engine: EngineType) -> list[dict]:
    if engine == "openai":
        return [{"id": v, "name": v, "locale": "", "gender": ""} for v in OPENAI_VOICES]

    if engine == "custom_http":
        return []

    if edge_tts is None:
        raise RuntimeError("edge-tts is not installed")

    global _EDGE_VOICES_CACHE, _EDGE_VOICES_CACHE_AT
    now = time.time()
    if _EDGE_VOICES_CACHE is not None and (now - _EDGE_VOICES_CACHE_AT) < _EDGE_VOICES_CACHE_TTL_SECONDS:
        return _EDGE_VOICES_CACHE["voices"]

    raw_voices = await edge_tts.list_voices()
    voices = []
    for item in raw_voices:
        voice_id = str(item.get("Name", "")).strip()
        if not voice_id:
            continue
        locale = str(item.get("Locale", "")).strip()
        gender = str(item.get("Gender", "")).strip()
        friendly = str(item.get("FriendlyName", "")).strip()
        display_name = friendly or voice_id
        voices.append(
            {
                "id": voice_id,
                "name": display_name,
                "locale": locale,
                "gender": gender,
            }
        )

    voices.sort(key=lambda x: (x["locale"], x["id"]))
    _EDGE_VOICES_CACHE = {"voices": voices}
    _EDGE_VOICES_CACHE_AT = now
    return voices


def _parse_headers_json(headers_json: str | None) -> dict:
    if not headers_json:
        return {}
    try:
        data = json.loads(headers_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"custom_headers_json is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("custom_headers_json must be a JSON object")
    return {str(k): str(v) for k, v in data.items()}


async def synthesize_custom_http(
    text: str,
    *,
    endpoint: str,
    api_key: str | None,
    model: str | None,
    voice: str | None,
    output_format: str,
    speed: float,
    custom_headers_json: str | None,
    timeout_seconds: int = 120,
) -> bytes:
    if not endpoint:
        raise ValueError("Custom HTTP engine requires endpoint")

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    headers.update(_parse_headers_json(custom_headers_json))

    payload = {
        "text": text,
        "model": model,
        "voice": voice,
        "format": output_format,
        "speed": speed,
    }

    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        resp = await client.post(endpoint, headers=headers, json=payload)
    if resp.status_code >= 400:
        detail = resp.text[:1000]
        raise RuntimeError(f"Custom HTTP API error {resp.status_code}: {detail}")
    return resp.content


async def synthesize_text(
    engine: EngineType,
    text: str,
    *,
    api_key: str | None,
    model: str | None,
    voice: str | None,
    output_format: str,
    speed: float,
    endpoint: str | None,
    instructions: str | None,
    custom_headers_json: str | None,
) -> bytes:
    if engine == "openai":
        return await synthesize_openai(
            text,
            api_key=api_key or "",
            model=model or "gpt-4o-mini-tts",
            voice=voice or "alloy",
            output_format=output_format,
            speed=speed,
            endpoint=endpoint,
            instructions=instructions,
        )
    if engine == "edge_tts":
        return await synthesize_edge_tts(text, voice=voice or DEFAULT_EDGE_VOICE, speed=speed)
    if engine == "custom_http":
        return await synthesize_custom_http(
            text,
            endpoint=endpoint or "",
            api_key=api_key,
            model=model,
            voice=voice,
            output_format=output_format,
            speed=speed,
            custom_headers_json=custom_headers_json,
        )
    raise ValueError(f"Unsupported engine: {engine}")
