import io
import math
import threading
import time
import wave
from functools import lru_cache
from typing import Callable, Optional, Tuple

import numpy as np
from scipy.signal import resample_poly


ASR_MODEL_ID = "facebook/mms-1b-all"
SAMPLE_RATE = 16_000
MAX_AUDIO_SECONDS = 30
LANGUAGE_CODES = {"Français": "fra", "Fon": "fon"}


class AssistantASRError(Exception):
    """A user-displayable error from the speech-recognition step."""


def read_wav_audio(audio_data: bytes) -> Tuple[int, np.ndarray]:
    try:
        with wave.open(io.BytesIO(audio_data), "rb") as wav_file:
            if wav_file.getcomptype() != "NONE" or wav_file.getsampwidth() != 2:
                raise AssistantASRError(
                    "Le microphone doit fournir un fichier WAV PCM 16 bits."
                )
            sample_rate = wav_file.getframerate()
            channels = wav_file.getnchannels()
            frames = wav_file.getnframes()
            if sample_rate <= 0 or channels <= 0:
                raise AssistantASRError("La fréquence ou les canaux du WAV sont invalides.")
            if frames / sample_rate > MAX_AUDIO_SECONDS:
                raise AssistantASRError(
                    f"L'audio dépasse la limite de {MAX_AUDIO_SECONDS} secondes."
                )
            samples = np.frombuffer(wav_file.readframes(frames), dtype="<i2")
    except AssistantASRError:
        raise
    except (EOFError, wave.Error) as error:
        raise AssistantASRError(
            "L'enregistrement reçu n'est pas un fichier WAV valide."
        ) from error

    if channels < 1 or samples.size != frames * channels:
        raise AssistantASRError("L'enregistrement WAV est incomplet ou invalide.")
    if channels > 1:
        samples = samples.reshape(-1, channels)
    return sample_rate, samples


@lru_cache(maxsize=1)
def _load_asr_model():
    import torch
    from transformers import AutoProcessor, Wav2Vec2ForCTC

    processor = AutoProcessor.from_pretrained(ASR_MODEL_ID, target_lang="fra")
    model = Wav2Vec2ForCTC.from_pretrained(
        ASR_MODEL_ID,
        target_lang="fra",
        ignore_mismatched_sizes=True,
    )
    model.load_adapter("fra")
    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    model.to(device)
    model.eval()
    return processor, model, device, torch


_MODEL_LOCK = threading.Lock()
_ACTIVE_LANGUAGE_CODE = "fra"


def _prepare_audio(audio: Optional[Tuple[int, np.ndarray]]) -> np.ndarray:
    if audio is None or not isinstance(audio, tuple) or len(audio) != 2:
        raise AssistantASRError("Enregistre ou sélectionne un fichier audio.")

    sample_rate, waveform = audio
    if not isinstance(sample_rate, (int, np.integer)) or sample_rate <= 0:
        raise AssistantASRError("La fréquence de l'audio est invalide.")

    samples = np.asarray(waveform)
    if samples.ndim == 2:
        if samples.shape[0] <= 2 and samples.shape[1] > 2:
            samples = samples.T
        samples = samples.mean(axis=1)
    if samples.ndim != 1 or samples.size == 0:
        raise AssistantASRError("L'audio est vide ou dans un format non pris en charge.")

    if np.issubdtype(samples.dtype, np.integer):
        limits = np.iinfo(samples.dtype)
        scale = max(abs(limits.min), limits.max)
        samples = samples.astype(np.float32) / scale
    else:
        samples = samples.astype(np.float32)
    if not np.isfinite(samples).all():
        raise AssistantASRError("L'audio contient des valeurs invalides.")

    if samples.size / sample_rate > MAX_AUDIO_SECONDS:
        raise AssistantASRError(
            f"L'audio dépasse la limite de {MAX_AUDIO_SECONDS} secondes."
        )

    samples = np.clip(samples, -1.0, 1.0)
    if sample_rate != SAMPLE_RATE:
        divisor = math.gcd(sample_rate, SAMPLE_RATE)
        samples = resample_poly(
            samples,
            SAMPLE_RATE // divisor,
            sample_rate // divisor,
        ).astype(np.float32)
    return samples


def transcribe_audio(
    audio: Optional[Tuple[int, np.ndarray]],
    language: str,
    progress: Optional[Callable[[str], None]] = None,
) -> str:
    try:
        target_language = LANGUAGE_CODES[language]
    except KeyError as error:
        raise AssistantASRError(
            "Choisis Français ou Fon comme langue de l'enregistrement."
        ) from error

    waveform = _prepare_audio(audio)
    if progress:
        progress("Chargement du modèle de reconnaissance…")
    model_load_started = time.perf_counter()
    processor, model, device, torch = _load_asr_model()
    if progress:
        model_load_seconds = time.perf_counter() - model_load_started
        progress(
            "Modèle prêt. Chargement terminé en "
            f"{model_load_seconds:.1f} s. Préparation de l'audio…"
        )

    global _ACTIVE_LANGUAGE_CODE
    with _MODEL_LOCK:
        if target_language != _ACTIVE_LANGUAGE_CODE:
            if progress:
                progress("Chargement de l'adaptateur de langue…")
            adapter_load_started = time.perf_counter()
            processor.tokenizer.set_target_lang(target_language)
            model.load_adapter(target_language)
            _ACTIVE_LANGUAGE_CODE = target_language
            if progress:
                progress(
                    "Adaptateur chargé en "
                    f"{time.perf_counter() - adapter_load_started:.1f} s."
                )

        if progress:
            progress("Analyse de la parole en cours…")
        inference_started = time.perf_counter()
        inputs = processor(
            waveform,
            sampling_rate=SAMPLE_RATE,
            return_tensors="pt",
        )
        inputs = {name: tensor.to(device) for name, tensor in inputs.items()}
        with torch.inference_mode():
            logits = model(**inputs).logits
        if device.type == "mps":
            torch.mps.synchronize()
        elif device.type == "cuda":
            torch.cuda.synchronize(device)
        if progress:
            progress(
                "Analyse terminée en "
                f"{time.perf_counter() - inference_started:.1f} s."
            )
            progress("Finalisation du texte reconnu…")
        finalization_started = time.perf_counter()
        token_ids = torch.argmax(logits, dim=-1)[0].cpu()
        transcription = processor.decode(token_ids).strip()
        if progress:
            progress(
                "Finalisation terminée en "
                f"{time.perf_counter() - finalization_started:.1f} s."
            )

    if not transcription:
        raise AssistantASRError(
            "Aucune parole n'a été reconnue. Vérifie l'audio ou essaie de parler "
            "plus près du micro."
        )
    if progress:
        progress("Transcription terminée.")
    return transcription
