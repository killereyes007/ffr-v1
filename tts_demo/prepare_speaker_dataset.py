import argparse
import csv
import json
import random
import unicodedata
import wave
from collections import Counter, defaultdict
from pathlib import Path

from transformers import AutoTokenizer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEECH_ROOT = PROJECT_ROOT / "Fongbe_Speech_Dataset"
METADATA_PATH = SPEECH_ROOT / "fongbe_speech_dataset_metadata.csv"
MODEL_ID = "facebook/mms-tts-fon"
SEED = 42


def transcript_key(text):
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def parse_args():
    parser = argparse.ArgumentParser(
        description="Validate one consenting adult speaker's Fon TTS pairs and split by text."
    )
    parser.add_argument("--speaker-id", required=True, help="Speaker ID from the metadata CSV.")
    parser.add_argument(
        "--consent-confirmed",
        action="store_true",
        help="Confirm explicit permission for TTS training and synthetic speech in this voice.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory (defaults to tts_demo/experiments/speaker_<id>).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace the generated train.csv, validation.csv, and quality_report.json.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.consent_confirmed:
        raise SystemExit(
            "Refusing to prepare voice-specific training data without "
            "--consent-confirmed."
        )

    with METADATA_PATH.open(encoding="utf-8-sig", newline="") as stream:
        metadata = list(csv.DictReader(stream))
    selected = [row for row in metadata if row["speaker ID"] == args.speaker_id]
    if not selected:
        raise SystemExit(f"No recordings found for speaker ID {args.speaker_id!r}.")

    ages = {int(row["age"]) for row in selected}
    if len(ages) != 1:
        raise SystemExit("Inconsistent ages in metadata for the selected speaker.")
    age = ages.pop()
    if age < 18:
        raise SystemExit("This preparation tool excludes recordings of minors.")

    output_dir = args.output_dir or (
        PROJECT_ROOT / "tts_demo" / "experiments" / f"speaker_{args.speaker_id}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = [output_dir / name for name in ("train.csv", "validation.csv", "quality_report.json")]
    existing = [path for path in outputs if path.exists()]
    if existing and not args.force:
        names = ", ".join(str(path) for path in existing)
        raise SystemExit(f"Generated outputs already exist ({names}); pass --force to replace them.")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    groups = defaultdict(list)
    durations = []
    formats = Counter()
    missing = []
    empty_transcripts = []
    records = []

    for row in selected:
        audio_path = SPEECH_ROOT / "fongbe_speech_audio_files" / "wav" / row["audio filename"]
        transcript_path = SPEECH_ROOT / "fongbe_speech_audio_files" / "lab" / row["transcription filename"]
        if not audio_path.is_file() or not transcript_path.is_file():
            missing.append(
                {
                    "audio": not audio_path.is_file(),
                    "transcript": not transcript_path.is_file(),
                    "audio_filename": row["audio filename"],
                    "transcription_filename": row["transcription filename"],
                }
            )
            continue

        text = unicodedata.normalize("NFC", transcript_path.read_text(encoding="utf-8")).strip()
        if not text:
            empty_transcripts.append(row["transcription filename"])
            continue

        try:
            with wave.open(str(audio_path), "rb") as audio:
                sample_rate = audio.getframerate()
                channels = audio.getnchannels()
                sample_width = audio.getsampwidth()
                frame_count = audio.getnframes()
        except (wave.Error, EOFError) as error:
            raise SystemExit(f"Unreadable WAV {audio_path}: {error}") from error

        if (sample_rate, channels, sample_width) != (16000, 1, 2):
            raise SystemExit(
                f"Unexpected audio format for {audio_path.name}: "
                f"{sample_rate} Hz, {channels} channel(s), {sample_width * 8}-bit PCM."
            )
        if frame_count == 0:
            raise SystemExit(f"Empty audio file: {audio_path}")

        input_ids = tokenizer(text, return_tensors="pt").input_ids[0].tolist()
        unknown_tokens = input_ids.count(tokenizer.unk_token_id)
        duration = frame_count / sample_rate
        record = {
            "audio_path": str(audio_path),
            "text": text,
            "speaker_id": args.speaker_id,
            "duration_seconds": round(duration, 3),
            "transcription_filename": row["transcription filename"],
            "unknown_token_count": unknown_tokens,
        }
        records.append(record)
        groups[transcript_key(text)].append(record)
        durations.append(duration)
        formats[(sample_rate, channels, sample_width * 8)] += 1

    if missing:
        raise SystemExit(f"Found {len(missing)} missing audio/transcript pair(s).")
    if empty_transcripts:
        raise SystemExit(f"Found {len(empty_transcripts)} empty transcription(s).")
    if not records:
        raise SystemExit("No usable audio/transcription pairs remain.")

    keys = list(groups)
    random.Random(SEED).shuffle(keys)
    validation_group_count = max(1, round(len(keys) * 0.1))
    validation_keys = set(keys[:validation_group_count])
    train_records = [
        record
        for key, group in groups.items()
        if key not in validation_keys
        for record in group
    ]
    validation_records = [
        record
        for key, group in groups.items()
        if key in validation_keys
        for record in group
    ]

    assert not (
        {transcript_key(row["text"]) for row in train_records}
        & {transcript_key(row["text"]) for row in validation_records}
    )
    assert len(train_records) + len(validation_records) == len(records)

    tokenizer_unknown_rows = sum(row["unknown_token_count"] > 0 for row in records)
    columns = ("audio_path", "text", "speaker_id", "duration_seconds")
    for path, split_records in (
        (output_dir / "train.csv", train_records),
        (output_dir / "validation.csv", validation_records),
    ):
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            writer.writerows({key: row[key] for key in columns} for row in split_records)

    report = {
        "source_metadata": str(METADATA_PATH),
        "model_tokenizer": MODEL_ID,
        "speaker_id": args.speaker_id,
        "speaker_age": age,
        "consent_confirmed_by_operator": True,
        "consent_scope_note": (
            "Operator confirmed permission for TTS training and generation using this voice; "
            "retain original consent documentation separately."
        ),
        "split_method": (
            "Deterministic 90/10 split by NFC-normalized, casefolded, whitespace-normalized "
            "transcript group; exact repeated texts are kept within one split."
        ),
        "random_seed": SEED,
        "source_rows_for_speaker": len(selected),
        "validated_pairs": len(records),
        "unique_transcript_groups": len(groups),
        "duplicate_transcript_rows": len(records) - len(groups),
        "train_rows": len(train_records),
        "train_unique_transcripts": len(
            {transcript_key(row["text"]) for row in train_records}
        ),
        "validation_rows": len(validation_records),
        "validation_unique_transcripts": len(
            {transcript_key(row["text"]) for row in validation_records}
        ),
        "transcript_groups_overlapping_splits": 0,
        "missing_files": len(missing),
        "empty_transcripts": len(empty_transcripts),
        "unreadable_audio_files": 0,
        "audio_formats": [
            {
                "sample_rate_hz": sample_rate,
                "channels": channels,
                "bits_per_sample": bits,
                "files": count,
            }
            for (sample_rate, channels, bits), count in sorted(formats.items())
        ],
        "total_audio_hours": round(sum(durations) / 3600, 3),
        "train_audio_hours": round(
            sum(row["duration_seconds"] for row in train_records) / 3600, 3
        ),
        "validation_audio_hours": round(
            sum(row["duration_seconds"] for row in validation_records) / 3600, 3
        ),
        "rows_with_tokenizer_unknown_tokens": tokenizer_unknown_rows,
        "source_filename_validation_marker_note": (
            "The source documentation describes validation as human review of recordings; "
            "it does not document a machine-learning train/test split."
        ),
    }
    (output_dir / "quality_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Prepared files: {output_dir}")


if __name__ == "__main__":
    main()
