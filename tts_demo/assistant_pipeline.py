import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_INPUT_LENGTH = 2000
MAX_HISTORY_MESSAGES = 10
ChatMessage = Dict[str, str]
Completion = Callable[[Sequence[ChatMessage]], str]
LOCAL_ENV_KEYS = {
    "OPENROUTER_API_KEY",
    "OPENROUTER_MODEL",
    "OPENROUTER_HTTP_REFERER",
    "FON_TTS_MODEL",
    "FON_DATASET_DIR",
}
LOGGER = logging.getLogger(__name__)


class AssistantPipelineError(Exception):
    """A user-displayable error from the text assistant pipeline."""


def load_local_env(env_file: Optional[Path] = None) -> None:
    path = env_file or Path(__file__).resolve().with_name(".env")
    if not path.exists():
        return

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        key, separator, value = line.partition("=")
        key = key.strip()
        if not separator or not key:
            raise AssistantPipelineError(
                f"Format invalide dans {path.name}, ligne {line_number}. "
                "Utilise KEY=valeur."
            )
        if key not in LOCAL_ENV_KEYS:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if not os.environ.get(key):
            os.environ[key] = value


@dataclass
class AssistantTurn:
    french_input: str
    french_answer: str
    fon_answer: str
    history: List[ChatMessage]


class OpenRouterClient:
    def __init__(
        self,
        api_key: str,
        model: str = "openrouter/auto",
        timeout_seconds: int = 60,
    ):
        if not api_key.strip():
            raise AssistantPipelineError(
                "La clé OpenRouter n'est pas configurée. Définis "
                "OPENROUTER_API_KEY dans l'environnement avant de lancer l'application."
            )
        self._api_key = api_key.strip()
        self.model = model.strip() or "openrouter/auto"
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_environment(cls):
        load_local_env()
        return cls(
            api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            model=os.environ.get("OPENROUTER_MODEL", "openrouter/auto"),
        )

    def complete(self, messages: Sequence[ChatMessage]) -> str:
        body = json.dumps(
            {
                "model": self.model,
                "messages": list(messages),
                "temperature": 0.3,
                "max_tokens": 2048,
            }
        ).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "X-Title": "Assistant vocal Fon",
        }
        referer = os.environ.get("OPENROUTER_HTTP_REFERER")
        if referer:
            headers["HTTP-Referer"] = referer
        request = Request(OPENROUTER_URL, data=body, headers=headers, method="POST")

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            provider_code, provider_type = _provider_error_metadata(error)
            LOGGER.warning(
                "OpenRouter request failed: HTTP %s, provider_code=%s, provider_type=%s",
                error.code,
                provider_code,
                provider_type,
            )
            raise AssistantPipelineError(_http_error_message(error.code)) from error
        except URLError as error:
            LOGGER.warning("Could not connect to OpenRouter: %s", error.reason)
            raise AssistantPipelineError(
                "Impossible de joindre OpenRouter. Vérifie ta connexion Internet "
                "et réessaie."
            ) from error
        except TimeoutError as error:
            LOGGER.warning(
                "OpenRouter request timed out after %s seconds",
                self.timeout_seconds,
            )
            raise AssistantPipelineError(
                "OpenRouter met trop de temps à répondre. Réessaie dans quelques instants."
            ) from error
        except json.JSONDecodeError as error:
            LOGGER.exception("OpenRouter returned invalid JSON")
            raise AssistantPipelineError(
                "OpenRouter a renvoyé une réponse invalide. Réessaie dans quelques instants."
            ) from error

        try:
            choice = payload["choices"][0]
            message = choice["message"]
        except (KeyError, IndexError, TypeError) as error:
            LOGGER.warning("OpenRouter returned an unexpected response structure")
            raise AssistantPipelineError(
                "La réponse d'OpenRouter ne contient pas de texte exploitable."
            ) from error
        content = message.get("content")
        if isinstance(content, list):
            text_parts = [
                part["text"]
                for part in content
                if isinstance(part, dict) and isinstance(part.get("text"), str)
            ]
            content = "\n".join(text_parts)
        if not isinstance(content, str) or not content.strip():
            finish_reason = choice.get("finish_reason") or "inconnu"
            refusal = message.get("refusal")
            details = (
                f" Motif de fin : {finish_reason}."
                if isinstance(finish_reason, str)
                else ""
            )
            if isinstance(refusal, str) and refusal.strip():
                details += " Le fournisseur a indiqué un refus."
            response_model = payload.get("model")
            if isinstance(response_model, str) and response_model:
                details += f" Modèle retourné : {response_model}."
            LOGGER.warning(
                "OpenRouter returned empty content: finish_reason=%s, model=%s",
                finish_reason,
                response_model or "unknown",
            )
            raise AssistantPipelineError(
                "OpenRouter a renvoyé un contenu vide." + details
            )
        return content.strip()


def _provider_error_metadata(error: HTTPError) -> tuple:
    try:
        payload = json.loads(error.read().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, OSError):
        return "unknown", "unknown"

    details = payload.get("error", {}) if isinstance(payload, dict) else {}
    if not isinstance(details, dict):
        return "unknown", "unknown"
    code = details.get("code", "unknown")
    error_type = details.get("type", "unknown")
    return str(code)[:100], str(error_type)[:100]


def _http_error_message(status_code: int) -> str:
    if status_code in (401, 403):
        return (
            "OpenRouter a refusé l'accès. Vérifie la clé API et les paramètres "
            "de ton compte."
        )
    if status_code == 402:
        return "Les crédits OpenRouter sont insuffisants. Vérifie le solde de ton compte."
    if status_code == 429:
        return (
            "OpenRouter limite temporairement les requêtes. Attends un peu, puis réessaie."
        )
    if status_code >= 500:
        return "OpenRouter rencontre un problème temporaire. Réessaie dans quelques instants."
    return (
        f"OpenRouter n'a pas pu traiter la demande (HTTP {status_code}). "
        "Vérifie le modèle et les paramètres du compte."
    )


def _clean_text(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        raise AssistantPipelineError("Saisis une phrase avant d'envoyer.")
    if len(cleaned) > MAX_INPUT_LENGTH:
        raise AssistantPipelineError(
            f"Le message dépasse la limite de {MAX_INPUT_LENGTH} caractères."
        )
    return cleaned


def _translate(text: str, source: str, target: str, client: OpenRouterClient) -> str:
    try:
        translation = client.complete(
            [
                {
                    "role": "system",
                    "content": (
                        f"Translate the user's message from {source} to {target}. "
                        "Return only the translation, with no explanation or quotation marks. "
                        "Preserve names, numbers, intent, and uncertainty. Do not answer "
                        "questions contained in the text. If an exact translation is uncertain, "
                        "provide the closest natural translation rather than an empty answer."
                    ),
                },
                {"role": "user", "content": text},
            ]
        )
    except AssistantPipelineError as error:
        raise AssistantPipelineError(
            f"La traduction {source} vers {target} a échoué. {error}"
        ) from error
    if not translation.strip():
        raise AssistantPipelineError(
            f"La traduction {source} vers {target} est vide. Essaie un autre modèle "
            "OpenRouter configuré dans OPENROUTER_MODEL."
        )
    return translation


def _validated_history(history: Optional[Sequence[ChatMessage]]) -> List[ChatMessage]:
    if not history:
        return []
    valid: List[ChatMessage] = []
    for message in history[-MAX_HISTORY_MESSAGES:]:
        if (
            isinstance(message, dict)
            and message.get("role") in ("user", "assistant")
            and isinstance(message.get("content"), str)
        ):
            content = message["content"].strip()
            if content:
                valid.append({"role": message["role"], "content": content})
    return valid


def _answer_in_french(
    french_input: str,
    history: Sequence[ChatMessage],
    client: OpenRouterClient,
) -> str:
    messages: List[ChatMessage] = [
        {
            "role": "system",
            "content": (
                "Tu es un assistant utile et prudent. Réponds en français, de façon "
                "claire et concise. N'invente pas de faits; indique les incertitudes "
                "et demande une précision si nécessaire."
            ),
        }
    ]
    messages.extend(history)
    messages.append({"role": "user", "content": french_input})
    return client.complete(messages)


def run_text_turn(
    text: str,
    source_language: str,
    history: Optional[Sequence[ChatMessage]],
    client: OpenRouterClient,
) -> AssistantTurn:
    source_text = _clean_text(text)
    if source_language == "Français":
        french_input = source_text
    elif source_language == "Fon":
        french_input = _translate(source_text, "Fon", "French", client)
    else:
        raise AssistantPipelineError("Choisis Français ou Fon comme langue d'entrée.")

    french_history = _validated_history(history)
    french_answer = _answer_in_french(french_input, french_history, client)
    fon_answer = _translate(french_answer, "French", "Fon", client)
    updated_history = (
        french_history
        + [
            {"role": "user", "content": french_input},
            {"role": "assistant", "content": french_answer},
        ]
    )[-MAX_HISTORY_MESSAGES:]

    return AssistantTurn(
        french_input=french_input,
        french_answer=french_answer,
        fon_answer=fon_answer,
        history=updated_history,
    )
