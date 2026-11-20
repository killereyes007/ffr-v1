import base64
import io
import json
import re
import tempfile
import unittest
import uuid
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient

import assistant_app


class AssistantAppTests(unittest.TestCase):
    @staticmethod
    def make_wav():
        output = io.BytesIO()
        with wave.open(output, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16_000)
            wav_file.writeframes(np.array([0, 1000, -1000], dtype="<i2").tobytes())
        return output.getvalue()

    def test_voice_turn_transcribes_then_generates_and_synthesizes_reply(self):
        events = []
        turn = SimpleNamespace(
            fon_answer="Fon response.",
            history=[{"role": "user", "content": "Bonjour"}],
        )
        audio = (16_000, np.array([0.0, 0.5, -0.5], dtype=np.float32))
        client = object()

        def fake_transcribe(_audio, _language, progress):
            progress("Analyse de la parole en cours…")
            return "Bonjour"

        with patch(
            "assistant_app.transcribe_audio",
            side_effect=fake_transcribe,
        ) as transcribe, patch(
            "assistant_app.run_text_turn",
            return_value=turn,
        ) as run_turn, patch(
            "assistant_app.synthesize",
            return_value=audio,
        ) as synthesize:
            transcription, result_turn, response_audio = assistant_app.process_voice_turn(
                (16_000, np.zeros(16, dtype=np.int16)),
                "Français",
                [],
                client,
                events.append,
            )

        self.assertEqual(transcription, "Bonjour")
        self.assertIs(result_turn, turn)
        self.assertIs(response_audio, audio)
        self.assertEqual(events[0]["type"], "progress")
        self.assertEqual(events[1], {"type": "transcript", "text": "Bonjour"})
        self.assertEqual(events[2]["message"], "Génération de la réponse…")
        self.assertEqual(events[3]["message"], "Synthèse vocale de la réponse…")
        run_turn.assert_called_once_with("Bonjour", "Français", [], client)
        synthesize.assert_called_once_with("Fon response.")
        transcribe.assert_called_once()

    def test_encode_audio_wav_returns_playable_mono_pcm(self):
        encoded = assistant_app.encode_audio_wav(
            (16_000, np.array([0.0, 0.5, -0.5], dtype=np.float32))
        )
        audio_bytes = base64.b64decode(encoded)

        with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
            self.assertEqual(wav_file.getframerate(), 16_000)
            self.assertEqual(wav_file.getnchannels(), 1)
            self.assertEqual(wav_file.getsampwidth(), 2)
            samples = np.frombuffer(wav_file.readframes(3), dtype="<i2")

        np.testing.assert_array_equal(samples, np.array([0, 16383, -16383]))

    def test_encode_audio_wav_rejects_invalid_audio(self):
        with self.assertRaisesRegex(ValueError, "audio invalide"):
            assistant_app.encode_audio_wav((16_000, np.array([np.nan])))

    def test_voice_turn_endpoint_streams_transcript_and_reply_audio(self):
        session_id = str(uuid.uuid4())
        turn = SimpleNamespace(
            history=[{"role": "user", "content": "Bonjour"}],
            fon_answer="Nouveau texte en fon.",
        )
        audio = (16_000, np.zeros(3, dtype=np.float32))
        assistant_app.VOICE_HISTORIES.clear()
        assistant_app.VOICE_SESSION_LOCKS.clear()

        def fake_process_voice_turn(
            _audio, _language, _history, _client, emit_event
        ):
            emit_event({"type": "transcript", "text": "Bonjour"})
            return "Bonjour", turn, audio

        with patch(
            "assistant_app.OpenRouterClient.from_environment",
            return_value=object(),
        ), patch(
            "assistant_app.read_wav_audio",
            return_value=audio,
        ), patch(
            "assistant_app.process_voice_turn",
            side_effect=fake_process_voice_turn,
        ), patch(
            "assistant_app.encode_audio_wav",
            return_value="encoded-audio",
        ):
            with TestClient(assistant_app.web_app) as client:
                response = client.post(
                    "/voice-turn?language=Français",
                    content=b"test audio",
                    headers={"X-Conversation-Id": session_id},
                )

        self.assertEqual(response.status_code, 200)
        self.assertIn('"type": "transcript", "text": "Bonjour"', response.text)
        self.assertIn('"type": "done", "audio": "encoded-audio"', response.text)
        self.assertIn('"fon_answer": "Nouveau texte en fon."', response.text)
        self.assertEqual(assistant_app.VOICE_HISTORIES[session_id], turn.history)
        assistant_app.VOICE_HISTORIES.clear()
        assistant_app.VOICE_SESSION_LOCKS.clear()

    def test_training_example_requires_explicit_consent(self):
        with TestClient(assistant_app.web_app) as client:
            response = client.post(
                "/training-examples",
                json={"consent": False},
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("consentement explicite", response.json()["detail"])

    def test_training_example_saves_corrected_text_and_original_audio(self):
        input_audio = self.make_wav()
        generated_audio = (16_000, np.array([0.0, 0.5, -0.5], dtype=np.float32))
        with tempfile.TemporaryDirectory() as dataset_directory, patch(
            "assistant_app.DATASET_DIR",
            Path(dataset_directory),
        ), patch(
            "assistant_app.synthesize",
            return_value=generated_audio,
        ) as synthesize:
            with TestClient(assistant_app.web_app) as client:
                response = client.post(
                    "/training-examples",
                    json={
                        "consent": True,
                        "language": "Fon",
                        "input_audio": base64.b64encode(input_audio).decode("ascii"),
                        "asr_transcript": "Original ASR.",
                        "input_transcript": "Transcription corrigée.",
                        "assistant_fon_text_original": "Réponse IA originale.",
                        "assistant_fon_text": "Réponse IA corrigée.",
                    },
                )

            self.assertEqual(response.status_code, 200, response.text)
            sample_id = response.json()["sample_id"]
            sample_directory = Path(dataset_directory) / sample_id
            metadata = json.loads(
                (sample_directory / "metadata.json").read_text(encoding="utf-8")
            )
            self.assertEqual((sample_directory / "input_audio.wav").read_bytes(), input_audio)
            self.assertTrue((sample_directory / "assistant_audio.wav").is_file())

        self.assertEqual(metadata["asr_transcript"], "Original ASR.")
        self.assertEqual(metadata["input_transcript"], "Transcription corrigée.")
        self.assertEqual(
            metadata["assistant_fon_text_original"],
            "Réponse IA originale.",
        )
        self.assertEqual(metadata["assistant_fon_text"], "Réponse IA corrigée.")
        self.assertEqual(
            metadata["assistant_audio_role"],
            "ai_synthesized_for_quality_review_not_human_tts_target",
        )
        synthesize.assert_called_once_with("Réponse IA corrigée.")

    def test_training_phrase_requires_consent_and_both_texts(self):
        with TestClient(assistant_app.web_app) as client:
            no_consent = client.post(
                "/training-phrases",
                json={
                    "consent": False,
                    "french_text": "Bonjour",
                    "fon_text": "Bonjour en fon",
                },
            )
            missing_translation = client.post(
                "/training-phrases",
                json={"consent": True, "french_text": "Bonjour"},
            )

        self.assertEqual(no_consent.status_code, 400)
        self.assertIn("consentement explicite", no_consent.json()["detail"])
        self.assertEqual(missing_translation.status_code, 400)
        self.assertIn("traduction en fon", missing_translation.json()["detail"])

    def test_game_page_is_served(self):
        with TestClient(assistant_app.web_app) as client:
            response = client.get("/game")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Le carnet des voix", response.text)
        asset_paths = re.findall(r'"/game-assets/([^"]+)"', response.text)
        js_asset_path = next(path for path in asset_paths if path.endswith(".js"))
        with TestClient(assistant_app.web_app) as client:
            asset_response = client.get(f"/game-assets/{js_asset_path}")

        self.assertEqual(asset_response.status_code, 200)
        self.assertIn("javascript", asset_response.headers["content-type"])
        self.assertTrue(asset_response.content)

    def test_home_page_presents_project_vision_and_prototype_paths(self):
        with TestClient(assistant_app.web_app) as client:
            response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Le fon mérite d’être", response.text)
        self.assertIn("Pourquoi FFR ?", response.text)
        self.assertIn("Comprendre. Traduire. Faire entendre.", response.text)
        self.assertIn("Le carnet des voix", response.text)
        self.assertIn("Découvrir l’assistant", response.text)

    def test_game_contribution_requires_human_audio(self):
        with TestClient(assistant_app.web_app) as client:
            response = client.post(
                "/training-phrases",
                json={
                    "consent": True,
                    "source": "game",
                    "mission_id": "radio-ouverture",
                    "mission_title": "Un premier message",
                    "french_text": "La radio est de retour.",
                    "fon_text": "Phrase en fon.",
                },
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("enregistrement vocal est requis", response.json()["detail"])

    def test_game_contribution_saves_consented_audio_without_synthesizing(self):
        human_audio = self.make_wav()
        with tempfile.TemporaryDirectory() as dataset_directory, patch(
            "assistant_app.DATASET_DIR",
            Path(dataset_directory),
        ), patch("assistant_app.synthesize") as synthesize:
            with TestClient(assistant_app.web_app) as client:
                response = client.post(
                    "/training-phrases",
                    json={
                        "consent": True,
                        "source": "game",
                        "mission_id": "radio-ouverture",
                        "mission_title": "Un premier message",
                        "french_text": "Bonjour à toutes et à tous, la radio est de retour.",
                        "fon_text": "Phrase proposée en fon.",
                        "human_audio": base64.b64encode(human_audio).decode("ascii"),
                    },
                )

            self.assertEqual(response.status_code, 200, response.text)
            self.assertIsNone(response.json()["synthesized_audio"])
            sample_id = response.json()["sample_id"]
            sample_directory = (
                Path(dataset_directory) / "phrase-pairs" / sample_id
            )
            metadata = json.loads(
                (sample_directory / "metadata.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                (sample_directory / "fon_human_reading.wav").read_bytes(),
                human_audio,
            )
            self.assertFalse((sample_directory / "fon_synthesized.wav").exists())

        self.assertEqual(metadata["contribution_source"], "game")
        self.assertEqual(metadata["review_status"], "unreviewed")
        self.assertEqual(metadata["mission_id"], "radio-ouverture")
        self.assertEqual(metadata["mission_title"], "Un premier message")
        self.assertIsNone(metadata["synthesized_audio_file"])
        self.assertEqual(metadata["human_audio_role"], "human_recording_for_review")
        synthesize.assert_not_called()

    def test_training_phrase_saves_human_audio_and_text_pair(self):
        human_audio = self.make_wav()
        synthesized_audio = assistant_app.encode_audio_wav(
            (16_000, np.array([0.0, 0.5, -0.5], dtype=np.float32))
        )
        with tempfile.TemporaryDirectory() as dataset_directory, patch(
            "assistant_app.DATASET_DIR",
            Path(dataset_directory),
        ), patch("assistant_app.synthesize") as synthesize:
            with TestClient(assistant_app.web_app) as client:
                response = client.post(
                    "/training-phrases",
                    json={
                        "consent": True,
                        "french_text": "Bonjour, comment vas-tu ?",
                        "fon_text": "Traduction en fon.",
                        "human_audio": base64.b64encode(human_audio).decode("ascii"),
                        "synthesized_audio": synthesized_audio,
                    },
                )

            self.assertEqual(response.status_code, 200, response.text)
            sample_id = response.json()["sample_id"]
            sample_directory = (
                Path(dataset_directory) / "phrase-pairs" / sample_id
            )
            metadata = json.loads(
                (sample_directory / "metadata.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                (sample_directory / "fon_human_reading.wav").read_bytes(),
                human_audio,
            )
            self.assertEqual(
                (sample_directory / "fon_synthesized.wav").read_bytes(),
                base64.b64decode(synthesized_audio),
            )

        self.assertEqual(metadata["french_text"], "Bonjour, comment vas-tu ?")
        self.assertEqual(metadata["fon_text"], "Traduction en fon.")
        self.assertEqual(metadata["contribution_source"], "training")
        self.assertEqual(metadata["review_status"], "unreviewed")
        self.assertEqual(metadata["human_audio_role"], "human_tts_training_target")
        self.assertEqual(
            metadata["synthesized_audio_role"],
            "ai_synthesized_for_review_not_human_tts_target",
        )
        synthesize.assert_not_called()

    def test_training_phrase_generates_synthesized_audio_when_not_previewed(self):
        generated_audio = (16_000, np.array([0.0, 0.5], dtype=np.float32))
        with tempfile.TemporaryDirectory() as dataset_directory, patch(
            "assistant_app.DATASET_DIR",
            Path(dataset_directory),
        ), patch(
            "assistant_app.synthesize",
            return_value=generated_audio,
        ) as synthesize:
            with TestClient(assistant_app.web_app) as client:
                response = client.post(
                    "/training-phrases",
                    json={
                        "consent": True,
                        "french_text": "Bonjour",
                        "fon_text": "Fon.",
                    },
                )

            self.assertEqual(response.status_code, 200, response.text)
            sample_id = response.json()["sample_id"]
            sample_directory = (
                Path(dataset_directory) / "phrase-pairs" / sample_id
            )
            metadata = json.loads(
                (sample_directory / "metadata.json").read_text(encoding="utf-8")
            )
            self.assertIsNone(metadata["human_audio_file"])
            self.assertTrue((sample_directory / "fon_synthesized.wav").is_file())

        synthesize.assert_called_once_with("Fon.")

    def test_training_synthesis_returns_encoded_wav(self):
        generated_audio = (16_000, np.array([0.0, 0.5], dtype=np.float32))
        with patch("assistant_app.synthesize", return_value=generated_audio) as synthesize:
            with TestClient(assistant_app.web_app) as client:
                response = client.post(
                    "/training-synthesis",
                    json={"fon_text": "Fon."},
                )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            base64.b64decode(response.json()["audio"]),
            base64.b64decode(assistant_app.encode_audio_wav(generated_audio)),
        )
        synthesize.assert_called_once_with("Fon.")


if __name__ == "__main__":
    unittest.main()
