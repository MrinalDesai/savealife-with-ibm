"""Local speech-to-text transcription using faster-whisper.

This module provides offline audio transcription for SaveAlife's voice input feature.
Uses faster-whisper for CPU-friendly, low-latency transcription without API calls.
"""

from typing import Optional
import io
import os
import tempfile

# Module-level cache so the model loads only once per session
_MODEL_CACHE = {}


def _get_model(model_size: str = "tiny", device: str = "cpu", compute_type: str = "int8"):
    """Lazily load and cache a faster-whisper WhisperModel.

    Default 'tiny' is ~75MB and runs in 2-3 seconds for a 10-second clip on CPU.
    The model is downloaded automatically by faster-whisper on first use.

    Args:
        model_size: Model size ('tiny', 'base', 'small', 'medium', 'large')
        device: Device to run on ('cpu' or 'cuda')
        compute_type: Quantization type ('int8', 'float16', 'float32')

    Returns:
        WhisperModel instance (cached)
    """
    cache_key = (model_size, device, compute_type)
    
    if cache_key not in _MODEL_CACHE:
        try:
            from faster_whisper import WhisperModel
            _MODEL_CACHE[cache_key] = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load faster-whisper model '{model_size}': {e}")
    
    return _MODEL_CACHE[cache_key]


def transcribe_audio_bytes(
    audio_bytes: bytes,
    model_size: str = "tiny",
    language: Optional[str] = "en"
) -> str:
    """Transcribe raw audio bytes to text using a local faster-whisper model.

    Args:
        audio_bytes: Raw audio data (WAV/WebM/etc — faster-whisper handles common formats via ctranslate2)
        model_size: 'tiny' (fastest), 'base', 'small' (better quality)
        language: ISO-639-1 code, or None to auto-detect. Default 'en' for speed.

    Returns:
        Transcribed text. Strips leading/trailing whitespace.

    Raises:
        RuntimeError with a clear message if transcription fails.
    """
    if not audio_bytes:
        return ""
    
    temp_path = None
    try:
        # Load model from cache
        model = _get_model(model_size=model_size)
        
        # Write audio bytes to a temporary file
        # faster-whisper expects a file path
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(audio_bytes)
        
        # Transcribe with beam_size=1 for speed (good enough for emergency dictation)
        segments, info = model.transcribe(
            temp_path,
            language=language,
            beam_size=1
        )
        
        # Join all segments' text into one string
        transcript_parts = []
        for segment in segments:
            transcript_parts.append(segment.text)
        
        transcript = " ".join(transcript_parts).strip()
        return transcript
        
    except Exception as e:
        raise RuntimeError(f"Transcription failed: {e}")
    
    finally:
        # Clean up temporary file
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception:
                pass  # Best effort cleanup

# Made with Bob
