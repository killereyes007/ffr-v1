import argparse
import csv
import json
import random
import wave
from pathlib import Path

import numpy as np
import torch
from transformers import AutoTokenizer, VitsModel, set_seed


MODEL_ID = "facebook/mms-tts-fon"


def load_model(model_id, device):
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = VitsModel.from_pretrained(model_id).to(device)
    model.eval()
    return tokenizer, model


def synthesize(text, tokenizer, model, device, destination, seed):
    set_seed(seed)
    inputs = tokenizer(text, return_tensors="pt")
    inputs = {name: value.to(device) for name, value in inputs.items()}
    with torch.inference_mode():
        audio = model(**inputs).waveform[0].detach().cpu().numpy()
    pcm = np.clip(audio, -1.0, 1.0)
    pcm = (pcm * 32767).astype(np.int16)
    with wave.open(str(destination), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(model.config.sampling_rate)
        stream.writeframes(pcm.tobytes())


def main():
    parser = argparse.ArgumentParser(
        description="Generate paired audio from the original and an adapted Fon TTS model."
    )
    parser.add_argument("--validation-csv", type=Path, required=True)
    parser.add_argument(
        "--adapted-model",
        help="Path or Hub ID for an adapted model. Omit to generate the original-model baseline only.",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1.")
    if not args.validation_csv.is_file():
        raise SystemExit(f"Validation CSV not found: {args.validation_csv}")

    with args.validation_csv.open(encoding="utf-8", newline="") as stream:
        examples = list(csv.DictReader(stream))
    if not examples:
        raise SystemExit("Validation CSV contains no examples.")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / "comparison.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        random.Random(args.seed).shuffle(examples)
        manifest = [
            {
                "text": example["text"],
                "reference_audio": example["audio_path"],
                "original_model_audio": str(args.output_dir / f"{index:03d}_original.wav"),
                "adapted_model_audio": None,
            }
            for index, example in enumerate(examples[: args.limit], start=1)
        ]

    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")

    base_tokenizer, base_model = load_model(MODEL_ID, device)
    if args.adapted_model:
        adapted_tokenizer, adapted_model = load_model(args.adapted_model, device)
    else:
        adapted_tokenizer, adapted_model = None, None

    for index, example in enumerate(manifest, start=1):
        seed = args.seed + index
        base_path = Path(example["original_model_audio"])
        if not base_path.is_file():
            synthesize(
                example["text"], base_tokenizer, base_model, device, base_path, seed
            )
        if adapted_model is not None:
            adapted_path = args.output_dir / f"{index:03d}_adapte.wav"
            synthesize(
                example["text"],
                adapted_tokenizer,
                adapted_model,
                device,
                adapted_path,
                seed,
            )
            example["adapted_model_audio"] = str(adapted_path)

    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Prepared {len(manifest)} held-out samples in {args.output_dir} using {device}. "
        + (
            "Original and adapted model audio are ready for listening."
            if adapted_model is not None
            else "Original-model baseline generated; pass --adapted-model later to complete comparisons."
        )
    )


if __name__ == "__main__":
    main()
