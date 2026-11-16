import argparse
import csv
import json
import tempfile
import unicodedata
import wave
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEECH_AUDIO_ROOT = (
    PROJECT_ROOT / "Fongbe_Speech_Dataset" / "fongbe_speech_audio_files" / "wav"
)
DEFAULT_EXPERIMENT_DIR = (
    Path(__file__).resolve().parent / "experiments" / "speaker_4"
)
CSV_COLUMNS = ("audio_path", "text", "duration_seconds")
REPORT_FIELDS = (
    "model_tokenizer",
    "split_method",
    "random_seed",
    "validated_pairs",
    "unique_transcript_groups",
    "duplicate_transcript_rows",
    "train_rows",
    "train_unique_transcripts",
    "validation_rows",
    "validation_unique_transcripts",
    "transcript_groups_overlapping_splits",
    "missing_files",
    "empty_transcripts",
    "unreadable_audio_files",
    "audio_formats",
    "total_audio_hours",
    "train_audio_hours",
    "validation_audio_hours",
    "rows_with_tokenizer_unknown_tokens",
)


def transcript_key(text):
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create a portable Colab bundle for the authorized speaker-4 experiment."
    )
    parser.add_argument(
        "--experiment-dir",
        type=Path,
        default=DEFAULT_EXPERIMENT_DIR,
        help="Directory containing train.csv, validation.csv, and quality_report.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Bundle path (defaults to <experiment-dir>/speaker_4_colab_bundle.zip).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing bundle.",
    )
    return parser.parse_args()


def read_split(path, split_name, audio_destinations):
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise SystemExit(f"{split_name} manifest is empty: {path}")

    portable_rows = []
    for row in rows:
        if row.get("speaker_id") != "4":
            raise SystemExit(
                f"Expected only authorized speaker 4 in {path}, got {row.get('speaker_id')!r}."
            )
        text = row.get("text", "").strip()
        if not text:
            raise SystemExit(f"Empty transcript in {path}")
        source = Path(row["audio_path"]).resolve(strict=True)
        if source.parent != SPEECH_AUDIO_ROOT.resolve():
            raise SystemExit(f"Audio is outside the expected speech dataset: {source}")
        if source.name in audio_destinations:
            raise SystemExit(f"Duplicate audio filename in manifests: {source.name}")
        try:
            with wave.open(str(source), "rb") as wav:
                audio_format = (
                    wav.getframerate(),
                    wav.getnchannels(),
                    wav.getsampwidth(),
                    wav.getnframes(),
                )
        except (wave.Error, EOFError) as error:
            raise SystemExit(f"Unreadable WAV {source}: {error}") from error
        if audio_format[:3] != (16000, 1, 2) or audio_format[3] == 0:
            raise SystemExit(f"Unexpected WAV format for {source}: {audio_format}")

        relative_audio_path = f"audio/{split_name}/{source.name}"
        audio_destinations[source.name] = (source, relative_audio_path, split_name)
        portable_rows.append(
            {
                "audio_path": relative_audio_path,
                "text": text,
                "duration_seconds": row["duration_seconds"],
            }
        )
    return portable_rows


def csv_bytes(rows):
    from io import StringIO

    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def main():
    args = parse_args()
    experiment_dir = args.experiment_dir.resolve()
    output_path = (args.output or experiment_dir / "speaker_4_colab_bundle.zip").resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and not args.force:
        raise SystemExit(f"Bundle already exists: {output_path}; pass --force to replace it.")

    manifests = {
        split: experiment_dir / f"{split}.csv"
        for split in ("train", "validation")
    }
    report_path = experiment_dir / "quality_report.json"
    comparison_path = experiment_dir / "comparison" / "comparison.json"
    for path in (*manifests.values(), report_path, comparison_path):
        if not path.is_file():
            raise SystemExit(f"Required experiment file not found: {path}")

    with report_path.open(encoding="utf-8") as stream:
        source_report = json.load(stream)
    if source_report.get("speaker_id") != "4" or source_report.get("speaker_age", 0) < 18:
        raise SystemExit("This package is restricted to the prepared adult speaker-4 experiment.")
    if source_report.get("consent_confirmed_by_operator") is not True:
        raise SystemExit("Refusing to package voice data without confirmed consent.")

    audio_destinations = {}
    rows_by_split = {
        split: read_split(path, split, audio_destinations)
        for split, path in manifests.items()
    }
    train_texts = {transcript_key(row["text"]) for row in rows_by_split["train"]}
    validation_texts = {
        transcript_key(row["text"]) for row in rows_by_split["validation"]
    }
    overlap = train_texts & validation_texts
    if overlap:
        raise SystemExit(
            f"Transcript leakage between train and validation: {len(overlap)} group(s)."
        )

    validation_audio_names = {
        source.name
        for source, _, split in audio_destinations.values()
        if split == "validation"
    }
    with comparison_path.open(encoding="utf-8") as stream:
        source_comparison = json.load(stream)
    comparison = []
    for index, item in enumerate(source_comparison, start=1):
        reference = Path(item["reference_audio"]).resolve(strict=True)
        original = Path(item["original_model_audio"]).resolve(strict=True)
        if reference.name not in validation_audio_names:
            raise SystemExit(
                f"Baseline reference is not part of this validation split: {reference}"
            )
        if original.parent != comparison_path.parent.resolve():
            raise SystemExit(f"Baseline audio is outside the comparison folder: {original}")
        comparison.append(
            {
                "text": item["text"],
                "reference_audio": f"audio/validation/{reference.name}",
                "original_model_audio": f"comparison/{index:03d}_original.wav",
                "adapted_model_audio": None,
            }
        )

    report = {key: source_report[key] for key in REPORT_FIELDS if key in source_report}
    report["portable_audio_files"] = len(audio_destinations)
    report["validation_transcript_overlap"] = len(overlap)

    readme = (
        "Fon TTS Colab pilot bundle\n"
        "==========================\n\n"
        "Contains only the approved adult speaker-4 audio/transcription pairs "
        "from the train and validation manifests, plus eight pre-generated "
        "MMS baseline audios for matched comparison.\n\n"
        "Audio format: mono, 16 kHz, 16-bit PCM WAV. Manifest audio_path values "
        "are relative to this bundle. Transcription groups do not overlap "
        "between train and validation.\n\n"
        "This voice-specific data is private. Use only in the consented TTS "
        "experiment; do not share the archive, voice recordings, or resulting "
        "checkpoint. The base MMS model is CC BY-NC 4.0; check that license "
        "before using or distributing any adapted model.\n"
    )

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            dir=output_path.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)

        with zipfile.ZipFile(
            temporary_path, "w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            archive.writestr("README.txt", readme)
            archive.writestr(
                "train.csv", csv_bytes(rows_by_split["train"])
            )
            archive.writestr(
                "validation.csv", csv_bytes(rows_by_split["validation"])
            )
            archive.writestr(
                "quality_report.json",
                json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            )
            archive.writestr(
                "comparison/comparison.json",
                json.dumps(comparison, ensure_ascii=False, indent=2) + "\n",
            )
            for source, relative_path, _ in audio_destinations.values():
                archive.write(source, relative_path)
            for index, item in enumerate(source_comparison, start=1):
                original = Path(item["original_model_audio"]).resolve(strict=True)
                archive.write(
                    original, f"comparison/{index:03d}_original.wav"
                )

        temporary_path.replace(output_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

    print(
        f"Created {output_path} with {len(rows_by_split['train'])} train pairs, "
        f"{len(rows_by_split['validation'])} validation pairs, "
        f"and {len(comparison)} matched baseline audios "
        f"({output_path.stat().st_size / (1024**2):.1f} MiB)."
    )


if __name__ == "__main__":
    main()
