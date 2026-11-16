import os
from functools import lru_cache
from pathlib import Path

import gradio as gr

from assistant_pipeline import load_local_env

load_local_env()

LOCAL_ADAPTED_MODEL = (
    Path(__file__).resolve().parent
    / "models"
    / "inference_model-speaker4-20261029"
)
if os.environ.get("FON_TTS_MODEL"):
    MODEL_ID = os.environ["FON_TTS_MODEL"]
elif (LOCAL_ADAPTED_MODEL / "config.json").is_file():
    MODEL_ID = str(LOCAL_ADAPTED_MODEL)
else:
    MODEL_ID = "facebook/mms-tts-fon"
MAX_TEXT_LENGTH = 500


def prepare_text(text):
    cleaned = text.strip()
    if not cleaned:
        raise gr.Error("Saisis une phrase en fon avant de lancer la génération.")
    if len(cleaned) > MAX_TEXT_LENGTH:
        raise gr.Error(
            "Le texte est trop long. La limite est de "
            f"{MAX_TEXT_LENGTH} caractères."
        )
    return cleaned


@lru_cache(maxsize=1)
def load_tts_model():
    import torch
    from transformers import AutoTokenizer, VitsModel

    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = VitsModel.from_pretrained(MODEL_ID)
    model.to(device)
    model.eval()
    return tokenizer, model, device, torch


def synthesize(text):
    text = prepare_text(text)
    tokenizer, model, device, torch = load_tts_model()
    inputs = tokenizer(text, return_tensors="pt")
    inputs = {name: tensor.to(device) for name, tensor in inputs.items()}

    with torch.inference_mode():
        waveform = model(**inputs).waveform[0].detach().cpu().numpy()

    return model.config.sampling_rate, waveform


with gr.Blocks(title="Tester la voix en fon") as demo:
    gr.Markdown(
        f"""
        # Tester la voix en fon

        Écris une phrase en fon puis écoute la synthèse vocale du modèle
        **{MODEL_ID}**. Cette page permet de tester le modèle chargé ; elle ne
        l'entraîne pas.
        """
    )

    text_input = gr.Textbox(
        label="Texte en fon",
        placeholder="Saisis ici une phrase en fon, avec ses accents et diacritiques.",
        lines=4,
        max_length=MAX_TEXT_LENGTH,
    )
    generate_button = gr.Button("Générer la voix", variant="primary")
    audio_output = gr.Audio(label="Audio généré", type="numpy")

    generate_button.click(
        fn=synthesize,
        inputs=text_input,
        outputs=audio_output,
        api_name=False,
    )

    gr.Markdown(
        f"""
        Le modèle et ses poids sont téléchargés depuis
        [Hugging Face](https://huggingface.co/{MODEL_ID}) au premier essai.
        La génération s'effectue sur cet ordinateur. Le modèle est sous
        licence **CC BY-NC 4.0** ; vérifie les conditions avant tout usage
        commercial.
        """
    )


if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", share=False)
