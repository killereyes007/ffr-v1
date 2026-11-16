import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError
from unittest.mock import patch

from assistant_pipeline import (
    AssistantPipelineError,
    OpenRouterClient,
    load_local_env,
    run_text_turn,
)


class FakeClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def complete(self, messages):
        self.calls.append(list(messages))
        return next(self.responses)


class AssistantPipelineTests(unittest.TestCase):
    def test_french_input_generates_french_answer_then_fon_translation(self):
        client = FakeClient(["La réponse.", "Réponse en fon."])

        turn = run_text_turn("Bonjour", "Français", [], client)

        self.assertEqual(turn.french_input, "Bonjour")
        self.assertEqual(turn.french_answer, "La réponse.")
        self.assertEqual(turn.fon_answer, "Réponse en fon.")
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(
            turn.history,
            [
                {"role": "user", "content": "Bonjour"},
                {"role": "assistant", "content": "La réponse."},
            ],
        )

    def test_fon_input_is_translated_before_answer(self):
        client = FakeClient(
            ["Bonjour, comment vas-tu ?", "Je vais bien.", "Réponse en fon."]
        )

        turn = run_text_turn("Wɛ ɖɔ?", "Fon", [], client)

        self.assertEqual(turn.french_input, "Bonjour, comment vas-tu ?")
        self.assertEqual(len(client.calls), 3)
        self.assertIn("from Fon to French", client.calls[0][0]["content"])
        self.assertEqual(
            client.calls[1][-1]["content"], "Bonjour, comment vas-tu ?"
        )

    def test_invalid_language_fails_without_calling_client(self):
        client = FakeClient([])
        with self.assertRaises(AssistantPipelineError):
            run_text_turn("Bonjour", "English", [], client)
        self.assertEqual(client.calls, [])

    def test_history_is_limited_to_last_five_turns(self):
        old_history = [
            item
            for index in range(7)
            for item in (
                {"role": "user", "content": f"question {index}"},
                {"role": "assistant", "content": f"answer {index}"},
            )
        ]
        client = FakeClient(["Nouvelle réponse.", "Fon."])

        turn = run_text_turn("Nouvelle question", "Français", old_history, client)

        self.assertEqual(len(client.calls[0]), 12)
        self.assertEqual(client.calls[0][1]["content"], "question 2")
        self.assertEqual(len(turn.history), 10)

    def test_openrouter_request_uses_configured_model_and_bearer_key(self):
        client = OpenRouterClient("test-key", model="test/model")
        response_data = {
            "choices": [{"message": {"content": "Bonjour."}}],
        }

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps(response_data).encode("utf-8")

        with patch("assistant_pipeline.urlopen", return_value=FakeResponse()) as open_url:
            result = client.complete([{"role": "user", "content": "Salut"}])

        request = open_url.call_args.args[0]
        self.assertEqual(result, "Bonjour.")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        self.assertEqual(
            json.loads(request.data)["model"],
            "test/model",
        )
        self.assertEqual(json.loads(request.data)["max_tokens"], 2048)

    def test_openrouter_http_errors_are_user_friendly_and_logged(self):
        client = OpenRouterClient("test-key")
        error_body = json.dumps(
            {"error": {"code": "rate_limit_exceeded", "type": "rate_limit"}}
        ).encode("utf-8")
        error = HTTPError(
            "https://openrouter.ai/api/v1/chat/completions",
            429,
            "Too Many Requests",
            None,
            io.BytesIO(error_body),
        )

        with patch("assistant_pipeline.urlopen", side_effect=error):
            with self.assertLogs("assistant_pipeline", level="WARNING") as logs:
                with self.assertRaisesRegex(
                    AssistantPipelineError,
                    "limite temporairement",
                ):
                    client.complete([{"role": "user", "content": "secret user text"}])

        self.assertIn("HTTP 429", logs.output[0])
        self.assertIn("rate_limit_exceeded", logs.output[0])
        self.assertNotIn("secret user text", logs.output[0])

    def test_openrouter_auth_error_suggests_checking_key_without_provider_details(self):
        client = OpenRouterClient("test-key")
        error = HTTPError(
            "https://openrouter.ai/api/v1/chat/completions",
            401,
            "Unauthorized",
            None,
            io.BytesIO(b'{"error":{"message":"sensitive provider detail"}}'),
        )

        with patch("assistant_pipeline.urlopen", side_effect=error):
            with self.assertRaisesRegex(
                AssistantPipelineError,
                "Vérifie la clé API",
            ) as raised:
                client.complete([{"role": "user", "content": "Hello"}])

        self.assertNotIn("sensitive provider detail", str(raised.exception))

    def test_openrouter_connection_and_timeout_errors_are_actionable(self):
        client = OpenRouterClient("test-key")

        with patch(
            "assistant_pipeline.urlopen",
            side_effect=URLError("offline"),
        ):
            with self.assertRaisesRegex(
                AssistantPipelineError,
                "connexion Internet",
            ):
                client.complete([{"role": "user", "content": "Hello"}])

        with patch("assistant_pipeline.urlopen", side_effect=TimeoutError):
            with self.assertRaisesRegex(
                AssistantPipelineError,
                "trop de temps",
            ):
                client.complete([{"role": "user", "content": "Hello"}])

    def test_openrouter_empty_response_reports_provider_diagnostics(self):
        response_data = {
            "model": "provider/test-model",
            "choices": [
                {
                    "message": {"content": None, "refusal": None},
                    "finish_reason": "length",
                }
            ],
        }

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps(response_data).encode("utf-8")

        client = OpenRouterClient("test-key", model="test/model")
        with patch("assistant_pipeline.urlopen", return_value=FakeResponse()):
            with self.assertRaisesRegex(
                AssistantPipelineError,
                "Motif de fin : length.*provider/test-model",
            ):
                client.complete([{"role": "user", "content": "Translate"}])

    def test_openrouter_accepts_text_blocks_in_content_array(self):
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": [
                            {"type": "text", "text": "  Fon phrase  "},
                            {"type": "image", "image_url": "ignored"},
                        ]
                    },
                    "finish_reason": "stop",
                }
            ],
        }

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps(response_data).encode("utf-8")

        client = OpenRouterClient("test-key", model="test/model")
        with patch("assistant_pipeline.urlopen", return_value=FakeResponse()):
            result = client.complete([{"role": "user", "content": "Translate"}])
        self.assertEqual(result, "Fon phrase")

    def test_local_env_file_loads_key_without_overriding_existing_environment(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            env_file = Path(temporary_directory) / ".env"
            env_file.write_text(
                'OPENROUTER_API_KEY="new-secret"\n'
                "OPENROUTER_MODEL=test/model\n",
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {"OPENROUTER_API_KEY": "already-exported"},
                clear=True,
            ):
                load_local_env(env_file)
                self.assertEqual(
                    os.environ["OPENROUTER_API_KEY"],
                    "already-exported",
                )
                self.assertEqual(os.environ["OPENROUTER_MODEL"], "test/model")

    def test_local_env_file_fills_an_empty_environment_value(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            env_file = Path(temporary_directory) / ".env"
            env_file.write_text(
                "OPENROUTER_API_KEY=new-secret\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}, clear=True):
                load_local_env(env_file)
                self.assertEqual(os.environ["OPENROUTER_API_KEY"], "new-secret")


if __name__ == "__main__":
    unittest.main()
