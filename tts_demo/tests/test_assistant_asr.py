import io
import unittest
import wave
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import torch

import assistant_asr
from assistant_asr import AssistantASRError, read_wav_audio, transcribe_audio


class FakeProcessor:
    def __init__(self):
        self.tokenizer = SimpleNamespace(set_target_lang=lambda language: None)
        self.sample_rate = None

    def __call__(self, waveform, sampling_rate, return_tensors):
        self.sample_rate = sampling_rate
        return {"input_values": torch.zeros((1, len(waveform)))}

    def decode(self, _token_ids):
        return "Bonjour."


class FakeModel:
    def __init__(self):
        self.loaded_adapters = []

    def to(self, _device):
        return self

    def eval(self):
        return self

    def load_adapter(self, language):
        self.loaded_adapters.append(language)

    def __call__(self, **_inputs):
        return SimpleNamespace(logits=torch.tensor([[[0.0, 1.0]]]))


class AssistantASRTests(unittest.TestCase):
    def test_load_asr_model_initializes_the_french_adapter(self):
        processor = FakeProcessor()
        model = FakeModel()
        assistant_asr._load_asr_model.cache_clear()
        try:
            with patch(
                "transformers.AutoProcessor.from_pretrained",
                return_value=processor,
            ), patch(
                "transformers.Wav2Vec2ForCTC.from_pretrained",
                return_value=model,
            ), patch("torch.cuda.is_available", return_value=False), patch(
                "torch.backends.mps.is_available",
                return_value=False,
            ):
                loaded_processor, loaded_model, device, _torch = (
                    assistant_asr._load_asr_model()
                )
        finally:
            assistant_asr._load_asr_model.cache_clear()

        self.assertIs(loaded_processor, processor)
        self.assertIs(loaded_model, model)
        self.assertEqual(device.type, "cpu")
        self.assertEqual(model.loaded_adapters, ["fra"])

    def test_read_wav_audio_reads_pcm16_recording(self):
        samples = np.array([0, 1000, -1000], dtype="<i2")
        audio_file = io.BytesIO()
        with wave.open(audio_file, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16_000)
            wav_file.writeframes(samples.tobytes())

        sample_rate, decoded = read_wav_audio(audio_file.getvalue())

        self.assertEqual(sample_rate, 16_000)
        np.testing.assert_array_equal(decoded, samples)

    def test_read_wav_audio_rejects_malformed_data(self):
        with self.assertRaisesRegex(AssistantASRError, "WAV valide"):
            read_wav_audio(b"not audio")

    def test_prepare_audio_converts_stereo_and_resamples_to_16khz(self):
        waveform = np.ones((48_000, 2), dtype=np.float32) * 0.25

        prepared = assistant_asr._prepare_audio((48_000, waveform))

        self.assertEqual(prepared.dtype, np.float32)
        self.assertEqual(prepared.shape, (16_000,))
        self.assertAlmostEqual(float(prepared.mean()), 0.25, places=3)

    def test_prepare_audio_normalizes_integer_pcm(self):
        waveform = np.array([0, 16_383, -16_384], dtype=np.int16)

        prepared = assistant_asr._prepare_audio((16_000, waveform))

        self.assertAlmostEqual(float(prepared[1]), 0.5, places=3)
        self.assertAlmostEqual(float(prepared[2]), -0.5, places=3)

    def test_prepare_audio_rejects_missing_and_oversized_audio(self):
        with self.assertRaises(AssistantASRError):
            assistant_asr._prepare_audio(None)
        with self.assertRaisesRegex(AssistantASRError, "30 secondes"):
            assistant_asr._prepare_audio(
                (16_000, np.zeros(16_000 * 31, dtype=np.float32))
            )

    def test_transcribe_audio_uses_selected_language_adapter(self):
        processor = FakeProcessor()
        model = FakeModel()
        progress_messages = []
        with patch(
            "assistant_asr._load_asr_model",
            return_value=(processor, model, torch.device("cpu"), torch),
        ), patch.object(assistant_asr, "_ACTIVE_LANGUAGE_CODE", "fra"):
            result = transcribe_audio(
                (16_000, np.zeros(16_000, dtype=np.float32)),
                "Fon",
                progress_messages.append,
            )

        self.assertEqual(result, "Bonjour.")
        self.assertEqual(model.loaded_adapters, ["fon"])
        self.assertEqual(processor.sample_rate, 16_000)
        self.assertEqual(progress_messages[0], "Chargement du modèle de reconnaissance…")
        self.assertTrue(progress_messages[1].startswith("Modèle prêt. Chargement terminé en "))
        self.assertEqual(progress_messages[2], "Chargement de l'adaptateur de langue…")
        self.assertTrue(progress_messages[3].startswith("Adaptateur chargé en "))
        self.assertEqual(progress_messages[4], "Analyse de la parole en cours…")
        self.assertTrue(progress_messages[5].startswith("Analyse terminée en "))
        self.assertEqual(progress_messages[6], "Finalisation du texte reconnu…")
        self.assertTrue(progress_messages[7].startswith("Finalisation terminée en "))
        self.assertEqual(progress_messages[8], "Transcription terminée.")

    def test_transcribe_audio_rejects_unknown_language(self):
        with self.assertRaisesRegex(AssistantASRError, "Français ou Fon"):
            transcribe_audio(
                (16_000, np.zeros(16_000, dtype=np.float32)),
                "Anglais",
            )


if __name__ == "__main__":
    unittest.main()
