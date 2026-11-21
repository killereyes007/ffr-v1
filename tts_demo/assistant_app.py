import asyncio
import base64
import binascii
import io
import json
import logging
import os
import shutil
import tempfile
import threading
import uuid
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import gradio as gr
import numpy as np
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from app import MODEL_ID, synthesize
from assistant_asr import (
    ASR_MODEL_ID,
    AssistantASRError,
    read_wav_audio,
    transcribe_audio,
)
from assistant_pipeline import (
    ChatMessage,
    AssistantPipelineError,
    OpenRouterClient,
    run_text_turn,
)

LOGGER = logging.getLogger(__name__)
VOICE_HISTORIES: Dict[str, List[ChatMessage]] = {}
VOICE_SESSION_LOCKS: Dict[str, asyncio.Lock] = {}
VOICE_SESSION_GUARD = threading.Lock()
DATASET_DIR = Path(
    os.environ.get(
        "FON_DATASET_DIR",
        str(Path.home() / "fon-assistant-training-data"),
    )
).expanduser()
MAX_TRAINING_REQUEST_BYTES = 18_000_000
GAME_FRONTEND_DIST = Path(__file__).resolve().parent / "frontend" / "dist"



def process_voice_turn(audio, language, history, client, emit_event):
    transcription = transcribe_audio(
        audio,
        language,
        lambda message: emit_event({"type": "progress", "message": message}),
    )
    emit_event({"type": "transcript", "text": transcription})
    emit_event({"type": "progress", "message": "Génération de la réponse…"})
    turn = run_text_turn(transcription, language, history, client)
    emit_event({"type": "progress", "message": "Synthèse vocale de la réponse…"})
    response_audio = synthesize(turn.fon_answer)
    return transcription, turn, response_audio


def wav_duration_seconds(raw_wav_bytes: bytes) -> float:
    with wave.open(io.BytesIO(raw_wav_bytes), "rb") as wav_file:
        frames = wav_file.getnframes()
        framerate = wav_file.getframerate()
        if not framerate:
            return 0.0
        return round(frames / framerate, 3)


def encode_audio_wav(audio) -> str:
    sample_rate, waveform = audio
    samples = np.asarray(waveform, dtype=np.float32)
    if samples.ndim != 1 or samples.size == 0 or not np.isfinite(samples).all():
        raise ValueError("Le modèle vocal a produit un audio invalide.")

    pcm_samples = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")
    output = io.BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_samples.tobytes())
    return base64.b64encode(output.getvalue()).decode("ascii")


def persist_training_example(
    audio_data,
    language,
    asr_transcript,
    input_transcript,
    assistant_fon_text_original,
    fon_answer,
    speaker_id=None,
    speaker_label=None,
):
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    sample_id = str(uuid.uuid4())
    response_audio = synthesize(fon_answer)
    response_audio_bytes = base64.b64decode(encode_audio_wav(response_audio))
    metadata = {
        "schema_version": 1,
        "sample_id": sample_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "consent": True,
        "speaker_id": speaker_id,
        "speaker_label": speaker_label,
        "input_language": language,
        "asr_transcript": asr_transcript,
        "input_transcript": input_transcript,
        "input_audio_file": "input_audio.wav",
        "input_audio_role": "user_recording_for_asr",
        "input_audio_duration_seconds": wav_duration_seconds(audio_data),
        "assistant_fon_text_original": assistant_fon_text_original,
        "assistant_fon_text": fon_answer,
        "assistant_audio_file": "assistant_audio.wav",
        "assistant_audio_role": "ai_synthesized_for_quality_review_not_human_tts_target",
        "assistant_audio_duration_seconds": wav_duration_seconds(response_audio_bytes),
        "asr_model": ASR_MODEL_ID,
        "tts_model": MODEL_ID,
    }

    with tempfile.TemporaryDirectory(prefix=".pending-", dir=DATASET_DIR) as temporary:
        staging_dir = Path(temporary)
        (staging_dir / "input_audio.wav").write_bytes(audio_data)
        (staging_dir / "assistant_audio.wav").write_bytes(response_audio_bytes)
        (staging_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(staging_dir, DATASET_DIR / sample_id)

    return sample_id, base64.b64encode(response_audio_bytes).decode("ascii")


def persist_training_phrase(
    french_text,
    fon_text,
    human_audio,
    synthesized_audio,
    contribution_source="free_collecte",
    mission_id=None,
    mission_title=None,
    generate_synthesis=True,
    speaker_id=None,
    speaker_label=None,
    self_reviewed=False,
):
    phrase_dir = DATASET_DIR / "phrase-pairs"
    phrase_dir.mkdir(parents=True, exist_ok=True)
    sample_id = str(uuid.uuid4())
    if synthesized_audio is None and generate_synthesis:
        synthesized_audio = base64.b64decode(encode_audio_wav(synthesize(fon_text)))
    human_audio_role = (
        "human_recording_for_review"
        if contribution_source == "game_mission"
        else "human_tts_training_target"
    )
    metadata = {
        "schema_version": 1,
        "sample_id": sample_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "consent": True,
        "speaker_id": speaker_id,
        "speaker_label": speaker_label,
        "contribution_source": contribution_source,
        "review_status": "self-reviewed" if self_reviewed else "unreviewed",
        "mission_id": mission_id,
        "mission_title": mission_title,
        "french_text": french_text,
        "fon_text": fon_text,
        "synthesized_audio_file": (
            "fon_synthesized.wav" if synthesized_audio else None
        ),
        "synthesized_audio_role": (
            "ai_synthesized_for_review_not_human_tts_target"
            if synthesized_audio
            else None
        ),
        "synthesized_audio_duration_seconds": (
            wav_duration_seconds(synthesized_audio) if synthesized_audio else None
        ),
        "human_audio_file": "fon_human_reading.wav" if human_audio else None,
        "human_audio_role": human_audio_role,
        "human_audio_duration_seconds": (
            wav_duration_seconds(human_audio) if human_audio else None
        ),
        "tts_model": MODEL_ID if synthesized_audio else None,
    }

    with tempfile.TemporaryDirectory(prefix=".pending-", dir=phrase_dir) as temporary:
        staging_dir = Path(temporary)
        if synthesized_audio:
            (staging_dir / "fon_synthesized.wav").write_bytes(synthesized_audio)
        if human_audio:
            (staging_dir / "fon_human_reading.wav").write_bytes(human_audio)
        (staging_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(staging_dir, phrase_dir / sample_id)

    encoded_synthesis = (
        base64.b64encode(synthesized_audio).decode("ascii")
        if synthesized_audio
        else None
    )
    return sample_id, encoded_synthesis


FONT_HEAD_TAGS = """
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link
  href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&family=Space+Grotesk:wght@400;500;600;700&display=swap"
  rel="stylesheet"
/>
"""


with gr.Blocks(title="FFR — Fon, français et voix", head=FONT_HEAD_TAGS) as demo:
    gr.HTML(
        """
        <div id="fon-landing" class="fon-landing">
          <header class="fon-site-header">
            <a class="fon-site-brand" href="/" aria-label="FFR — accueil">
              <span class="fon-site-mark" aria-hidden="true">F</span>
              <span><strong>FFR</strong><small>Fon · français · voix</small></span>
            </a>
            <nav class="fon-site-nav" aria-label="Navigation principale">
              <a href="#vision">Notre vision</a>
              <a href="#demarche">Notre démarche</a>
              <a href="/game">Le carnet des voix</a>
              <a class="fon-site-nav-cta" href="/game?screen=assistant">Essayer le prototype <span aria-hidden="true">↗</span></a>
            </nav>
          </header>
          <main class="fon-landing-content">
            <section class="fon-landing-hero">
              <div class="fon-landing-copy">
                <span class="fon-eyebrow"><span class="fon-eyebrow-dot"></span> Un projet de recherche et de création au Bénin</span>
                <h1>Le fon mérite d’être <em>entendu.</em></h1>
                <p>FFR explore comment la technologie peut rapprocher le fon et le français — par la traduction, la voix et des ressources construites avec soin.</p>
                <div class="fon-hero-actions">
                  <a class="fon-primary-action" href="/game?screen=assistant">Découvrir l’assistant <span aria-hidden="true">↗</span></a>
                  <a class="fon-secondary-action" href="#vision">Découvrir le projet <span aria-hidden="true">↓</span></a>
                </div>
                <p class="fon-hero-note"><span aria-hidden="true">◉</span> Un prototype en évolution, pas encore un service de traduction certifié.</p>
              </div>
              <div class="fon-landing-art" aria-hidden="true">
                <div class="fon-art-orbit fon-art-orbit-one"></div>
                <div class="fon-art-orbit fon-art-orbit-two"></div>
                <div class="fon-art-sun"></div>
                <div class="fon-art-core"><span>Fɔ̀ngbè</span><small>UNE LANGUE, DES VOIX</small></div>
                <span class="fon-art-word fon-art-word-one">àgbọ̀</span>
                <span class="fon-art-word fon-art-word-two">ɖò</span>
                <span class="fon-art-word fon-art-word-three">wémɛ̀</span>
                <div class="fon-art-waveform"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div>
                <span class="fon-art-caption">BÉNIN <b>·</b> LANGUE VIVANTE <b>·</b> AVENIR PARTAGÉ</span>
              </div>
            </section>
            <section class="fon-project-intro" id="vision">
              <div class="fon-section-heading">
                <span class="fon-eyebrow">Pourquoi FFR ?</span>
                <h2>Une langue vivante mérite des outils à sa mesure.</h2>
              </div>
              <div class="fon-project-copy">
                <p>Le fon — fɔngbè — se parle, se transmet et évolue au quotidien. Pourtant, les outils numériques qui comprennent et font entendre les langues africaines restent rares. FFR veut contribuer à changer cela, en partant des données, des voix et des réalités du Bénin.</p>
                <p>Notre ambition : des technologies utiles, évaluées avec les locuteurs, qui soutiennent la transmission sans prétendre remplacer les personnes ni figer une langue diverse.</p>
              </div>
              <div class="fon-facts" aria-label="Repères du projet">
                <div><strong>53 975</strong><span>paires Fon–français dans le corpus historique principal</span></div>
                <div><strong>3 179</strong><span>entrées dans le manifeste du corpus vocal présent</span></div>
                <div><strong>Avec les locuteurs</strong><span>la qualité et les usages doivent être évalués par la communauté</span></div>
              </div>
            </section>
            <section class="fon-approach" id="demarche">
              <div class="fon-section-heading">
                <span class="fon-eyebrow">De la recherche à l’expérience</span>
                <h2>Comprendre. Traduire. Faire entendre.</h2>
                <p>Un parcours expérimental qui relie la parole aux outils de langue.</p>
              </div>
              <div class="fon-approach-cards">
                <article class="fon-approach-card">
                  <span class="fon-approach-number">01 <span aria-hidden="true">⌁</span></span>
                  <h3>Écouter la parole</h3>
                  <p>Un prototype de reconnaissance vocale explore l’entrée en français et en fon. Sa précision en fon reste à mesurer avec des locuteurs.</p>
                </article>
                <article class="fon-approach-card">
                  <span class="fon-approach-number">02 <span aria-hidden="true">↔</span></span>
                  <h3>Relier les langues</h3>
                  <p>Les corpus Fon–français et les modèles de traduction forment le socle de recherche. Les traductions automatiques peuvent se tromper.</p>
                </article>
                <article class="fon-approach-card">
                  <span class="fon-approach-number">03 <span aria-hidden="true">♫</span></span>
                  <h3>Donner une voix</h3>
                  <p>La synthèse vocale permet d’écouter du texte en fon. La qualité, la prononciation et les usages doivent encore être évalués.</p>
                </article>
              </div>
            </section>
            <section class="fon-vision-band">
              <span class="fon-eyebrow">Notre vision</span>
              <blockquote>La technologie doit aider les langues à prendre leur place — et laisser leurs locuteurs en garder la voix.</blockquote>
              <p>Des outils accessibles, des données documentées, une évaluation humaine et un développement responsable.</p>
            </section>
            <section class="fon-explore">
              <div class="fon-section-heading">
                <span class="fon-eyebrow">Explorer le prototype</span>
                <h2>La vision prend forme, étape par étape.</h2>
              </div>
              <div class="fon-mode-cards">
                <a id="fon-open-chat" class="fon-mode-card" href="/game?screen=assistant">
                  <span class="fon-card-topline"><span class="fon-mode-icon" aria-hidden="true">◉</span><span class="fon-card-tag">Prototype vocal</span></span>
                  <strong>Essayer l’assistant</strong>
                  <span>Découvre le parcours de conversation, de la parole à une réponse audio en fon.</span>
                  <span class="fon-mode-action">Ouvrir l’assistant <b aria-hidden="true">→</b></span>
                </a>
                <a class="fon-mode-card fon-game-card" href="/game">
                  <span class="fon-card-topline"><span class="fon-mode-icon">♫</span><span class="fon-card-tag">Expérience narrative</span></span>
                  <strong>Le carnet des voix</strong>
                  <span>Explore un chapitre pilote autour d’une radio fictive et de la parole au quotidien.</span>
                  <span class="fon-mode-action">Explorer le carnet <b aria-hidden="true">→</b></span>
                </a>
                <a id="fon-open-training" class="fon-mode-card" href="/game?screen=game&mode=free">
                  <span class="fon-card-topline"><span class="fon-mode-icon fon-mode-icon-training" aria-hidden="true">Aa</span><span class="fon-card-tag">Contribution</span></span>
                  <strong>Découvrir la collecte</strong>
                  <span>Propose ta propre phrase en français et sa traduction en fon, puis lis-la à voix haute.</span>
                  <span class="fon-mode-action">Voir le parcours <b aria-hidden="true">→</b></span>
                </a>
              </div>
            </section>
            <section class="fon-responsibility">
              <span class="fon-responsibility-mark" aria-hidden="true">i</span>
              <div><strong>Un prototype, développé avec responsabilité.</strong><p>Les contributions ne sont enregistrées qu’avec consentement explicite et restent à vérifier. Une voix générée par l’IA n’est pas une voix humaine de référence. Le projet ne remplace ni l’expertise des locuteurs, ni une validation communautaire.</p></div>
            </section>
          </main>
          <footer class="fon-site-footer">
            <a class="fon-site-brand" href="/" aria-label="FFR — accueil">
              <span class="fon-site-mark" aria-hidden="true">F</span>
              <span><strong>FFR</strong><small>Fon · français · voix</small></span>
            </a>
            <p>Une recherche en devenir, ancrée au Bénin.</p>
            <a href="/game">Explorer Le carnet des voix <span aria-hidden="true">↗</span></a>
          </footer>
        </div>
        <style>
          :root { color-scheme: dark; }
          body {
            background: radial-gradient(ellipse at 18% 72%, rgba(0, 194, 255, .16), transparent 38%),
              radial-gradient(ellipse at 86% 20%, rgba(11, 60, 93, .4), transparent 34%),
              #0a2540 !important;
          }
          .gradio-container {
            width:100% !important; max-width:none !important; min-height:100vh;
            padding:0 34px 32px !important;
            background:radial-gradient(ellipse at 18% 72%,rgba(0,194,255,.16),transparent 38%),
              radial-gradient(ellipse at 86% 20%,rgba(11,60,93,.4),transparent 34%),#0a2540 !important;
          }
          footer { display: none !important; }
          #fon-voice-interface { width: 100%; }
          [hidden] { display:none !important; }
          #fon-voice-interface #fon-landing {
            min-height:calc(100vh - 32px); display:flex; flex-direction:column;
            color:#e6f7ff !important; font-family:"IBM Plex Sans",ui-sans-serif,system-ui,sans-serif;
            background:radial-gradient(ellipse at 12% 75%,rgba(0,194,255,.14),transparent 38%),
              radial-gradient(ellipse at 88% 8%,rgba(11,60,93,.35),transparent 34%),#0a2540 !important;
            padding-bottom:106px; box-sizing:border-box;
          }
          #fon-voice-interface .fon-landing-brand { display:flex; align-items:center; gap:12px; min-height:82px; border-bottom:1px solid rgba(255,255,255,.1); }
          #fon-voice-interface .fon-landing-brand strong,#fon-voice-interface .fon-landing-brand span { display:block; }
          #fon-voice-interface .fon-landing-brand strong { color:#fff !important; }
          #fon-voice-interface .fon-landing-brand div span { margin-top:3px; color:#aeb5d7 !important; font-size:13px; }
          #fon-voice-interface .fon-landing-content { width:min(1000px,100%); margin:auto; padding:42px 0 30px; }
          #fon-voice-interface .fon-landing-hero {
            display:grid; grid-template-columns:minmax(0,1.05fr) minmax(280px,.95fr);
            align-items:center; gap:36px; padding:clamp(28px,5vw,58px);
            overflow:hidden; border:1px solid rgba(230,247,255,.12); border-radius:30px;
            background:radial-gradient(ellipse at 82% 18%,rgba(0,194,255,.12),transparent 40%),
              linear-gradient(135deg,rgba(11,60,93,.85),rgba(10,37,64,.9));
            box-shadow:0 24px 70px rgba(0,0,0,.2);
          }
          #fon-voice-interface .fon-landing-copy { text-align:left; }
          #fon-voice-interface .fon-eyebrow { color:#00c2ff !important; font-size:11px; font-weight:800; letter-spacing:.16em; text-transform:uppercase; font-family:"Space Grotesk",ui-sans-serif,sans-serif; }
          #fon-voice-interface .fon-landing-copy h1 { max-width:9ch; margin:15px 0 14px; color:#e6f7ff !important; font-family:"Space Grotesk",ui-sans-serif,sans-serif; font-size:clamp(38px,5.4vw,64px); line-height:.99; letter-spacing:-.045em; }
          #fon-voice-interface .fon-landing-copy p { max-width:430px; margin:0; color:rgba(230,247,255,.85) !important; font-size:16px; line-height:1.7; }
          #fon-voice-interface .fon-landing-art {
            position:relative; min-height:290px; overflow:hidden; isolation:isolate;
            border:1px solid rgba(255,255,255,.13); border-radius:24px;
            background:radial-gradient(ellipse at 50% 37%,rgba(255,203,107,.75),transparent 3%),
              linear-gradient(180deg,#71527b 0%,#d18470 44%,#f3b96d 68%,#23375b 69%,#182647 100%);
          }
          #fon-voice-interface .fon-art-sun { position:absolute; top:15%; right:19%; width:66px; aspect-ratio:1; border-radius:50%; background:#ffd278; box-shadow:0 0 55px rgba(255,210,120,.55); }
          #fon-voice-interface .fon-art-hill { position:absolute; z-index:-1; bottom:0; width:120%; height:43%; border-radius:50% 50% 0 0; }
          #fon-voice-interface .fon-art-hill-back { left:-45%; background:#31456b; }
          #fon-voice-interface .fon-art-hill-front { right:-53%; height:35%; background:#1b3150; }
          #fon-voice-interface .fon-art-station { position:absolute; bottom:17%; left:13%; width:39%; height:36%; border:3px solid rgba(255,226,179,.75); border-bottom:0; border-radius:9px 9px 0 0; background:linear-gradient(145deg,#edb67d,#bd795f); box-shadow:0 10px 24px rgba(10,17,40,.24); }
          #fon-voice-interface .fon-art-sign { position:absolute; top:10%; left:12%; padding:3px 7px; border-radius:4px; background:#243653; color:#ffe09a; font-size:9px; font-weight:900; letter-spacing:.12em; }
          #fon-voice-interface .fon-art-window { position:absolute; top:40%; left:13%; width:25%; height:28%; border:3px solid #293d5c; background:#f7d291; }
          #fon-voice-interface .fon-art-door { position:absolute; right:14%; bottom:0; width:23%; height:43%; border-radius:8px 8px 0 0; background:#72524d; }
          #fon-voice-interface .fon-art-tower { position:absolute; z-index:1; right:24%; bottom:18%; width:2px; height:57%; background:#f7d79d; }
          #fon-voice-interface .fon-art-tower-mast { position:absolute; left:-21px; top:0; width:44px; height:2px; background:#f7d79d; }
          #fon-voice-interface .fon-art-tower-cross { position:absolute; left:-11px; top:28%; width:24px; height:2px; background:#f7d79d; }
          #fon-voice-interface .fon-art-wave { position:absolute; top:5%; width:42px; height:42px; border:1px solid rgba(255,225,164,.8); border-radius:50%; }
          #fon-voice-interface .fon-art-wave-one { left:-42px; }
          #fon-voice-interface .fon-art-wave-two { left:-64px; top:-9%; width:86px; height:86px; opacity:.65; }
          #fon-voice-interface .fon-art-radio { position:absolute; right:8%; bottom:12%; display:grid; gap:8px; width:118px; padding:13px; border:1px solid rgba(255,255,255,.3); border-radius:12px; background:rgba(17,26,54,.88); box-shadow:0 12px 24px rgba(10,17,40,.25); color:#ffd970; font-size:9px; font-weight:900; letter-spacing:.14em; }
          #fon-voice-interface .fon-art-equalizer { display:flex; align-items:center; gap:4px; height:25px; }
          #fon-voice-interface .fon-art-equalizer i { width:5px; height:35%; border-radius:5px; background:#ffd970; }
          #fon-voice-interface .fon-art-equalizer i:nth-child(2n) { height:75%; }
          #fon-voice-interface .fon-art-equalizer i:nth-child(3n) { height:100%; }
          #fon-voice-interface .fon-art-caption { position:absolute; left:15px; bottom:13px; color:rgba(255,255,255,.75); font-size:9px; font-weight:800; letter-spacing:.16em; }
          #fon-voice-interface .fon-mode-heading { display:flex; justify-content:space-between; align-items:end; gap:16px; margin:38px 0 16px; }
          #fon-voice-interface .fon-mode-heading h2 { margin:7px 0 0; color:#fff !important; font-size:clamp(21px,3vw,27px); letter-spacing:-.025em; }
          #fon-voice-interface .fon-mode-count { padding:8px 12px; border:1px solid rgba(255,255,255,.12); border-radius:999px; color:#b9c0df !important; font-size:12px; white-space:nowrap; }
          #fon-voice-interface .fon-mode-cards { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px; text-align:left; }
          #fon-voice-interface .fon-mode-card {
            display:flex !important; flex-direction:column; align-items:flex-start; min-width:0; min-height:220px; padding:21px;
            border:1px solid rgba(230,247,255,.13) !important; border-radius:20px;
            background:linear-gradient(150deg,rgba(11,60,93,.85),rgba(10,37,64,.9)) !important;
            color:#e6f7ff !important; text-align:left; font:inherit; cursor:pointer;
            transition:transform .18s ease,border-color .18s ease,box-shadow .18s ease;
            text-decoration:none !important; box-shadow:0 12px 28px rgba(0,0,0,.12);
          }
          #fon-voice-interface .fon-mode-card:hover { transform:translateY(-4px); border-color:rgba(0,194,255,.65) !important; background:linear-gradient(150deg,#0b3c5d,#0a2540) !important; box-shadow:0 18px 34px rgba(0,0,0,.22),0 0 30px rgba(0,194,255,.12); }
          #fon-voice-interface .fon-mode-card:focus-visible { outline:3px solid #00c2ff; outline-offset:3px; }
          #fon-voice-interface .fon-game-card { border-color:rgba(0,194,255,.42) !important; background:linear-gradient(150deg,rgba(11,60,93,.95),rgba(10,37,64,.95)) !important; }
          #fon-voice-interface .fon-card-topline { display:flex; align-items:center; justify-content:space-between; width:100%; margin-bottom:21px; }
          #fon-voice-interface .fon-mode-icon { display:grid; place-items:center; width:43px; height:43px; border-radius:14px; background:rgba(0,194,255,.16); color:#00c2ff !important; font-size:23px; font-weight:800; }
          #fon-voice-interface .fon-mode-icon-training { font-size:17px; }
          #fon-voice-interface .fon-card-tag { color:rgba(230,247,255,.8) !important; font-size:10px; font-weight:750; letter-spacing:.08em; text-transform:uppercase; }
          #fon-voice-interface .fon-mode-card strong { color:#fff !important; font-family:"Space Grotesk",ui-sans-serif,sans-serif; font-size:17px; line-height:1.3; }
          #fon-voice-interface .fon-mode-card > span:not(.fon-card-topline) { margin-top:8px; color:rgba(230,247,255,.72) !important; font-size:13px; line-height:1.55; }
          #fon-voice-interface .fon-mode-card .fon-mode-action { display:flex; align-items:center; justify-content:space-between; gap:8px; width:100%; margin-top:auto !important; padding-top:22px; color:#00c2ff !important; font-size:13px; font-weight:750; }
          #fon-voice-interface .fon-mode-action b { font-size:19px; transition:transform .18s ease; }
          #fon-voice-interface .fon-mode-card:hover .fon-mode-action b { transform:translateX(3px); }
          #fon-voice-interface .fon-landing-note { width:min(1000px,100%); margin:0 auto 18px; color:#aeb5d7 !important; font-size:12px; line-height:1.6; }
          #fon-voice-interface .fon-home-nav {
            position:fixed; z-index:1000; right:0; bottom:0; left:0;
            display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:8px;
            padding:10px 24px calc(10px + env(safe-area-inset-bottom));
            border-top:1px solid rgba(255,255,255,.16);
            background:rgba(13,17,42,.99); box-shadow:0 -12px 30px rgba(5,9,27,.32);
            backdrop-filter:blur(16px); -webkit-backdrop-filter:blur(16px);
          }
          #fon-voice-interface .fon-home-nav-item {
            display:flex; flex-direction:column; align-items:center; justify-content:center; gap:3px;
            min-height:62px; padding:4px 8px; border:1px solid transparent; border-radius:14px;
            background:rgba(255,255,255,.035); color:#c0c8e0 !important;
            -webkit-text-fill-color:#c0c8e0; font:inherit;
            font-size:13px; font-weight:750; line-height:1.2; text-align:center; opacity:1;
            text-decoration:none !important; cursor:pointer;
          }
          #fon-voice-interface .fon-home-nav-item > span:first-child {
            color:inherit; -webkit-text-fill-color:currentColor; font-size:25px; line-height:1;
          }
          #fon-voice-interface .fon-home-nav-item:hover { color:#fff !important; -webkit-text-fill-color:#fff; }
          #fon-voice-interface .fon-home-nav-item.is-active {
            border-color:rgba(255,211,72,.28); background:rgba(255,211,72,.12);
            color:#ffd348 !important; -webkit-text-fill-color:#ffd348;
          }
          #fon-voice-interface .fon-home-nav-item:focus-visible { outline:2px solid #ffd348; outline-offset:2px; }
          @media (max-width:800px) {
            .gradio-container { padding:0 20px 24px !important; }
            #fon-voice-interface { width:calc(100% + 64px) !important; max-width:none !important; margin-left:-32px !important; }
            .fon-header {
              display:grid; grid-template-columns:minmax(0,1fr) auto; gap:10px;
              min-height:0; padding:10px 0 14px;
            }
            .fon-brand { min-width:0; }
            .fon-brand strong { font-size:15px; }
            .fon-brand div span { font-size:12px; }
            .fon-back-button { padding:9px 12px; font-size:12px; }
            .fon-language { grid-column:1 / -1; justify-content:space-between; }
            .fon-language select { min-width:0; }
            .fon-layout { grid-template-columns:1fr; gap:18px; padding:18px 0; }
            .fon-guide-halo { min-height:0; }
            #fon-guide { height:min(42vh,360px); }
            #fon-mic-start { min-height:56px; min-width:210px; }
            .fon-transcript-panel { min-height:0; padding:24px; }
            #fon-voice-interface .fon-landing-content { padding:34px 0 24px; }
            #fon-voice-interface .fon-landing-hero { grid-template-columns:1fr; gap:24px; padding:30px; }
            #fon-voice-interface .fon-landing-copy h1 { max-width:12ch; }
            #fon-voice-interface .fon-landing-art { min-height:250px; }
            #fon-voice-interface .fon-mode-heading { margin-top:30px; }
            #fon-voice-interface .fon-mode-cards { grid-template-columns:1fr; gap:12px; }
            #fon-voice-interface .fon-mode-card { min-height:185px; }
            .fon-training-layout { min-height:auto; padding:24px 0; }
          }
          @media (max-width:420px) {
            .gradio-container { padding:0 14px 20px !important; }
            .fon-brand-mark { width:36px; height:36px; }
            .fon-brand strong { font-size:15px; }
            .fon-language { gap:6px; font-size:12px; }
            .fon-language select { min-width:100px; padding:9px 26px 9px 10px; }
            #fon-voice-interface .fon-landing-brand { min-height:72px; }
            #fon-voice-interface .fon-landing-hero { gap:18px; padding:22px; border-radius:24px; }
            #fon-voice-interface .fon-landing-copy h1 { font-size:40px; }
            #fon-voice-interface .fon-landing-copy p { font-size:14px; }
            #fon-voice-interface .fon-landing-art { min-height:205px; border-radius:19px; }
            #fon-voice-interface .fon-mode-heading { align-items:flex-start; flex-direction:column; gap:10px; margin-top:26px; }
            #fon-voice-interface .fon-mode-card { min-height:170px; padding:18px; }
            #fon-voice-interface .fon-card-topline { margin-bottom:15px; }
            .fon-back-button { padding:9px 12px; font-size:12px; }
          }
          @media (min-width:431px) {
            .gradio-container {
              display:flex; width:100%; height:100dvh; min-height:100dvh;
              box-sizing:border-box; align-items:center; justify-content:center;
              overflow:hidden; padding:0 !important;
            }
            #fon-voice-interface {
              position:relative; flex:none; width:min(430px,100%) !important;
              height:min(900px,calc(100dvh - 24px)); min-height:min(600px,calc(100dvh - 24px));
              overflow:hidden; margin:0 auto !important; border:1px solid rgba(255,255,255,.16);
              border-radius:36px;
              background:radial-gradient(ellipse at 0% 10%,rgba(99,76,174,.13),transparent 23rem),
                linear-gradient(160deg,#171d3d 0%,#10152f 56%,#101a33 100%);
              box-shadow:0 32px 90px rgba(0,0,0,.5),inset 0 1px rgba(255,255,255,.12);
            }
            #fon-voice-interface #fon-landing {
              position:absolute; inset:0; width:100%; height:100%; min-height:0;
              overflow:hidden; padding:8px 18px 0; border:0; border-radius:inherit;
              box-shadow:none;
            }
            #fon-voice-interface #fon-chat-screen,
            #fon-voice-interface #fon-training-screen {
              position:absolute; inset:0; width:100%; height:100%; min-height:0;
              overflow-x:hidden; overflow-y:auto; overscroll-behavior:contain;
              padding:8px 18px; border-radius:inherit;
              background:radial-gradient(ellipse at 18% 72%,rgba(52,73,190,.32),transparent 38%),
                radial-gradient(ellipse at 86% 20%,rgba(106,34,96,.18),transparent 34%),#101435;
            }
            #fon-voice-interface .fon-page,
            #fon-voice-interface .fon-training-screen { min-height:100%; }
            #fon-voice-interface .fon-header {
              display:grid; grid-template-columns:minmax(0,1fr) auto; gap:10px;
              min-height:0; padding:10px 0 14px;
            }
            #fon-voice-interface .fon-brand { min-width:0; }
            #fon-voice-interface .fon-brand strong { font-size:15px; }
            #fon-voice-interface .fon-brand div span { font-size:12px; }
            #fon-voice-interface .fon-back-button { padding:9px 12px; font-size:12px; }
            #fon-voice-interface .fon-language {
              grid-column:1 / -1; justify-content:space-between; gap:10px;
            }
            #fon-voice-interface .fon-language select { min-width:0; }
            #fon-voice-interface .fon-landing-brand { min-height:74px; flex:none; }
            #fon-voice-interface .fon-landing-content {
              display:flex; width:100%; min-height:0; flex:1 1 auto; flex-direction:column;
              overflow-y:auto; margin:0; padding:18px 0 14px; scrollbar-width:thin;
            }
            #fon-voice-interface .fon-landing-content > * { flex:0 0 auto; }
            #fon-voice-interface .fon-landing-hero {
              grid-template-columns:1fr; gap:18px; padding:21px; border-radius:24px;
            }
            #fon-voice-interface .fon-landing-copy h1 { max-width:12ch; font-size:40px; }
            #fon-voice-interface .fon-landing-copy p { font-size:14px; }
            #fon-voice-interface .fon-landing-art { min-height:205px; border-radius:19px; }
            #fon-voice-interface .fon-mode-heading {
              align-items:flex-start; flex-direction:column; gap:10px; margin:22px 0 14px;
            }
            #fon-voice-interface .fon-mode-cards { grid-template-columns:1fr; gap:12px; }
            #fon-voice-interface .fon-mode-card { min-height:160px; padding:18px; }
            #fon-voice-interface .fon-card-topline { margin-bottom:15px; }
            #fon-voice-interface .fon-landing-note { margin:16px 2px 4px; }
            #fon-voice-interface .fon-home-nav {
              position:absolute; right:0; bottom:0; left:0; padding-right:14px; padding-left:14px;
              border-radius:0 0 35px 35px;
            }
          }
          #fon-voice-interface #fon-landing {
            min-height:100vh; padding:0 clamp(20px,5vw,76px) 0;
            overflow:visible; border:0; border-radius:0;
            background:
              radial-gradient(ellipse at 82% 4%,rgba(0,194,255,.14),transparent 30%),
              radial-gradient(ellipse at 8% 52%,rgba(11,60,93,.4),transparent 34%),
              #0a2540 !important;
          }
          #fon-voice-interface .fon-site-header {
            display:flex; width:min(1220px,100%); min-height:86px; flex:none;
            align-items:center; justify-content:space-between; gap:28px;
            margin:0 auto; border-bottom:1px solid rgba(230,247,255,.1);
          }
          #fon-voice-interface .fon-site-brand {
            display:inline-flex; flex:none; align-items:center; gap:11px;
            color:#fff !important; text-decoration:none !important;
          }
          #fon-voice-interface .fon-site-mark {
            display:grid; width:42px; height:42px; place-items:center;
            border:1px solid rgba(0,194,255,.5); border-radius:14px;
            background:linear-gradient(145deg,#00c2ff,#0ea5e9); color:#0a2540;
            font-family:"Space Grotesk",ui-sans-serif,sans-serif; font-size:23px; font-weight:900;
          }
          #fon-voice-interface .fon-site-brand strong,
          #fon-voice-interface .fon-site-brand small { display:block; }
          #fon-voice-interface .fon-site-brand strong { color:#fff !important; font-family:"Space Grotesk",ui-sans-serif,sans-serif; font-size:17px; letter-spacing:.04em; }
          #fon-voice-interface .fon-site-brand small { margin-top:3px; color:rgba(230,247,255,.65) !important; font-size:11px; }
          #fon-voice-interface .fon-site-nav {
            display:flex; align-items:center; justify-content:flex-end; gap:clamp(14px,2.4vw,32px);
          }
          #fon-voice-interface .fon-site-nav > a,
          #fon-voice-interface .fon-site-footer > a:last-child {
            color:rgba(230,247,255,.8) !important; font-size:13px; font-weight:650;
            text-decoration:none !important; transition:color .18s ease;
          }
          #fon-voice-interface .fon-site-nav > a:hover,
          #fon-voice-interface .fon-site-footer > a:last-child:hover { color:#00c2ff !important; }
          #fon-voice-interface .fon-site-nav-cta,
          #fon-voice-interface .fon-primary-action {
            display:inline-flex; align-items:center; justify-content:center; gap:12px;
            min-height:46px; padding:0 18px; border:0; border-radius:999px;
            background:#00c2ff; color:#0a2540; font:inherit; font-size:13px;
            font-weight:800; text-transform:uppercase; letter-spacing:.04em; cursor:pointer;
            transition:transform .18s ease,filter .18s ease; box-shadow:0 0 30px rgba(0,194,255,.25);
          }
          #fon-voice-interface .fon-site-nav-cta:hover,
          #fon-voice-interface .fon-primary-action:hover { transform:translateY(-2px); filter:brightness(1.05); }
          #fon-voice-interface .fon-landing-content {
            display:block; width:min(1120px,100%); min-height:0; flex:none;
            overflow:visible; margin:0 auto; padding:52px 0 56px;
          }
          #fon-voice-interface .fon-landing-hero {
            grid-template-columns:minmax(0,1.08fr) minmax(330px,.92fr);
            gap:clamp(32px,6vw,82px); padding:clamp(36px,6vw,76px) 0;
            overflow:visible; border:0; border-radius:0; background:none; box-shadow:none;
          }
          #fon-voice-interface .fon-landing-copy { text-align:left; }
          #fon-voice-interface .fon-eyebrow {
            display:inline-flex; align-items:center; gap:9px; color:#00c2ff !important;
            font-size:11px; font-weight:800; letter-spacing:.15em; text-transform:uppercase;
          }
          #fon-voice-interface .fon-eyebrow-dot { width:7px; height:7px; border-radius:50%; background:#00c2ff; box-shadow:0 0 15px rgba(0,194,255,.7); }
          #fon-voice-interface .fon-landing-copy h1 {
            max-width:10ch; margin:23px 0 19px; color:#fff !important;
            font-family:"Space Grotesk",ui-sans-serif,sans-serif;
            font-size:clamp(48px,6.6vw,82px); font-weight:800; line-height:.99;
            letter-spacing:-.06em;
          }
          #fon-voice-interface .fon-landing-copy h1 em { color:#00c2ff; font-style:normal; }
          #fon-voice-interface .fon-landing-copy > p:not(.fon-hero-note) {
            max-width:555px; margin:0; color:rgba(230,247,255,.85) !important;
            font-size:clamp(16px,1.7vw,19px); line-height:1.75;
          }
          #fon-voice-interface .fon-hero-actions { display:flex; flex-wrap:wrap; align-items:center; gap:13px; margin-top:29px; }
          #fon-voice-interface .fon-primary-action { min-height:54px; padding:0 23px; font-size:14px; }
          #fon-voice-interface .fon-secondary-action {
            display:inline-flex; align-items:center; gap:10px; min-height:50px; padding:0 15px;
            color:#e6f7ff !important; font-size:14px; font-weight:700; text-decoration:none !important;
          }
          #fon-voice-interface .fon-secondary-action:hover { color:#00c2ff !important; }
          #fon-voice-interface .fon-hero-note { display:flex; align-items:center; gap:9px; margin:22px 0 0; color:rgba(230,247,255,.55) !important; font-size:12px; line-height:1.5; }
          #fon-voice-interface .fon-hero-note span { color:#00c2ff; }
          #fon-voice-interface .fon-landing-art {
            display:grid; min-height:405px; place-items:center; overflow:hidden; isolation:isolate;
            border:1px solid rgba(230,247,255,.1); border-radius:50% 50% 38% 38% / 44% 44% 28% 28%;
            background:
              radial-gradient(ellipse at 50% 48%,rgba(0,194,255,.14),transparent 44%),
              linear-gradient(155deg,rgba(11,60,93,.75),rgba(10,37,64,.96));
            box-shadow:inset 0 0 80px rgba(255,255,255,.025),0 30px 90px rgba(0,0,0,.2);
          }
          #fon-voice-interface .fon-art-orbit { position:absolute; width:67%; aspect-ratio:1; border:1px solid rgba(0,194,255,.18); border-radius:50%; transform:rotate(-26deg) scaleY(.55); }
          #fon-voice-interface .fon-art-orbit-one { width:85%; }
          #fon-voice-interface .fon-art-orbit-two { width:110%; border-color:rgba(230,247,255,.09); transform:rotate(28deg) scaleY(.45); }
          #fon-voice-interface .fon-art-sun { position:absolute; top:19%; right:19%; width:12px; height:12px; background:#00c2ff; box-shadow:0 0 22px #00c2ff; }
          #fon-voice-interface .fon-art-core { z-index:1; display:flex; width:174px; height:174px; flex-direction:column; align-items:center; justify-content:center; gap:10px; border:1px solid rgba(0,194,255,.45); border-radius:50%; background:radial-gradient(circle at 35% 25%,#0f4a74,#0a2540 76%); box-shadow:0 0 0 14px rgba(0,194,255,.035),0 0 70px rgba(0,194,255,.28); }
          #fon-voice-interface .fon-art-core > span { color:#fff; font-family:"Space Grotesk",ui-sans-serif,sans-serif; font-size:30px; font-weight:700; }
          #fon-voice-interface .fon-art-core small { color:#00c2ff; font-size:8px; font-weight:800; letter-spacing:.16em; }
          #fon-voice-interface .fon-art-word { position:absolute; z-index:2; padding:9px 13px; border:1px solid rgba(230,247,255,.16); border-radius:999px; background:rgba(11,37,64,.88); color:#e6f7ff; font-family:"Space Grotesk",ui-sans-serif,sans-serif; font-size:15px; box-shadow:0 8px 24px rgba(0,0,0,.18); }
          #fon-voice-interface .fon-art-word-one { top:22%; left:13%; }
          #fon-voice-interface .fon-art-word-two { top:41%; right:8%; }
          #fon-voice-interface .fon-art-word-three { bottom:25%; left:15%; }
          #fon-voice-interface .fon-art-waveform { position:absolute; right:15%; bottom:22%; left:15%; display:flex; height:31px; align-items:center; justify-content:center; gap:5px; }
          #fon-voice-interface .fon-art-waveform i { width:3px; height:25%; border-radius:4px; background:#00c2ff; opacity:.8; }
          #fon-voice-interface .fon-art-waveform i:nth-child(3n) { height:70%; }
          #fon-voice-interface .fon-art-waveform i:nth-child(4n) { height:100%; }
          #fon-voice-interface .fon-art-waveform i:nth-child(5n) { height:48%; }
          #fon-voice-interface .fon-art-caption { position:absolute; bottom:9%; color:rgba(230,247,255,.6); font-size:8px; font-weight:800; letter-spacing:.17em; }
          #fon-voice-interface .fon-project-intro { display:grid; grid-template-columns:.85fr 1.15fr; gap:20px 70px; padding:62px 0 68px; border-top:1px solid rgba(230,247,255,.1); }
          #fon-voice-interface .fon-section-heading h2 { max-width:18ch; margin:12px 0 0; color:#fff !important; font-family:"Space Grotesk",ui-sans-serif,sans-serif; font-size:clamp(28px,4vw,43px); line-height:1.12; letter-spacing:-.04em; }
          #fon-voice-interface .fon-section-heading > p { margin:12px 0 0; color:rgba(230,247,255,.65) !important; font-size:15px; line-height:1.65; }
          #fon-voice-interface .fon-project-copy { align-self:center; }
          #fon-voice-interface .fon-project-copy p { margin:0 0 13px; color:rgba(230,247,255,.85) !important; font-size:15px; line-height:1.8; }
          #fon-voice-interface .fon-facts { grid-column:1 / -1; display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); margin-top:20px; border:1px solid rgba(230,247,255,.11); border-radius:18px; background:rgba(230,247,255,.035); }
          #fon-voice-interface .fon-facts > div { display:flex; min-height:112px; flex-direction:column; justify-content:center; gap:7px; padding:20px 24px; }
          #fon-voice-interface .fon-facts > div + div { border-left:1px solid rgba(230,247,255,.1); }
          #fon-voice-interface .fon-facts strong { color:#00c2ff !important; font-family:"Space Grotesk",ui-sans-serif,sans-serif; font-size:clamp(20px,2.5vw,27px); letter-spacing:-.03em; }
          #fon-voice-interface .fon-facts span { max-width:30ch; color:rgba(230,247,255,.65) !important; font-size:12px; line-height:1.5; }
          #fon-voice-interface .fon-approach { padding:66px 0 72px; border-top:1px solid rgba(230,247,255,.1); }
          #fon-voice-interface .fon-approach > .fon-section-heading { max-width:680px; }
          #fon-voice-interface .fon-approach-cards { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:15px; margin-top:30px; }
          #fon-voice-interface .fon-approach-card { min-height:206px; padding:25px; border:1px solid rgba(230,247,255,.11); border-radius:18px; background:linear-gradient(145deg,rgba(11,60,93,.7),rgba(10,37,64,.6)); }
          #fon-voice-interface .fon-approach-number { display:flex; justify-content:space-between; color:#00c2ff !important; font-size:12px; font-weight:800; letter-spacing:.1em; }
          #fon-voice-interface .fon-approach-number span { font-size:20px; }
          #fon-voice-interface .fon-approach-card h3 { margin:23px 0 9px; color:#fff !important; font-family:"Space Grotesk",ui-sans-serif,sans-serif; font-size:19px; }
          #fon-voice-interface .fon-approach-card p { margin:0; color:rgba(230,247,255,.72) !important; font-size:13px; line-height:1.7; }
          #fon-voice-interface .fon-vision-band { padding:clamp(28px,5vw,58px); border:1px solid rgba(0,194,255,.2); border-radius:24px; background:radial-gradient(ellipse at 90% 15%,rgba(0,194,255,.14),transparent 38%),linear-gradient(130deg,rgba(11,60,93,.92),rgba(10,37,64,.92)); }
          #fon-voice-interface .fon-vision-band blockquote { max-width:900px; margin:18px 0 16px; color:#fff !important; font-family:"Space Grotesk",ui-sans-serif,sans-serif; font-size:clamp(25px,4vw,43px); line-height:1.24; letter-spacing:-.025em; }
          #fon-voice-interface .fon-vision-band > p { margin:0; color:rgba(230,247,255,.85) !important; font-size:14px; line-height:1.6; }
          #fon-voice-interface .fon-explore { padding:70px 0 48px; }
          #fon-voice-interface .fon-explore .fon-section-heading { margin-bottom:25px; }
          #fon-voice-interface .fon-mode-cards { grid-template-columns:repeat(3,minmax(0,1fr)); gap:15px; }
          #fon-voice-interface .fon-mode-card { min-height:230px; padding:23px; }
          #fon-voice-interface .fon-mode-card > span:not(.fon-card-topline) { font-size:13px; }
          #fon-voice-interface .fon-responsibility { display:flex; align-items:flex-start; gap:16px; margin-top:15px; padding:21px 23px; border:1px solid rgba(230,247,255,.1); border-radius:16px; background:rgba(10,37,64,.4); }
          #fon-voice-interface .fon-responsibility-mark { display:grid; width:26px; height:26px; flex:none; place-items:center; border:1px solid rgba(0,194,255,.45); border-radius:50%; color:#00c2ff; font-family:"Space Grotesk",ui-sans-serif,sans-serif; font-weight:700; }
          #fon-voice-interface .fon-responsibility strong { color:#fff !important; font-size:13px; }
          #fon-voice-interface .fon-responsibility p { margin:6px 0 0; color:rgba(230,247,255,.65) !important; font-size:12px; line-height:1.65; }
          #fon-voice-interface .fon-site-footer { display:flex; width:min(1120px,100%); min-height:100px; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:16px; margin:0 auto; border-top:1px solid rgba(230,247,255,.1); }
          #fon-voice-interface .fon-site-footer > p { margin:0; color:rgba(230,247,255,.55) !important; font-size:12px; }
          #fon-voice-interface .fon-site-footer > a:last-child { display:inline-flex; align-items:center; gap:8px; }
          #fon-voice-interface .fon-landing [hidden] { display:none !important; }
          @media (min-width:431px) {
            .main:has(#fon-landing:not([hidden])),
            .wrap:has(#fon-landing:not([hidden])),
            .contain:has(#fon-landing:not([hidden])),
            #component-7:has(#fon-landing:not([hidden])) {
              width:100%; max-width:none; min-width:0; flex:1 1 auto;
            }
            .gradio-container:has(#fon-landing:not([hidden])) {
              display:block; width:100%; height:auto; min-height:100dvh; overflow:visible;
              padding:0 !important; align-items:stretch; justify-content:stretch;
            }
            #fon-voice-interface:has(#fon-landing:not([hidden])) {
              position:relative; flex:none; width:100% !important; max-width:none;
              height:auto; min-height:100dvh; overflow:visible; margin:0 !important;
              border:0; border-radius:0; background:#0a2540; box-shadow:none;
            }
            #fon-voice-interface:has(#fon-landing:not([hidden])) #fon-landing {
              position:relative; inset:auto; width:100%; height:auto; min-height:100dvh;
              overflow:visible; padding:0 clamp(20px,5vw,76px);
            }
          }
          @media (max-width:800px) {
            #fon-voice-interface #fon-landing { padding:0 22px 0; }
            #fon-voice-interface .fon-site-header { min-height:76px; gap:14px; }
            #fon-voice-interface .fon-site-nav { gap:13px; }
            #fon-voice-interface .fon-site-nav > a { display:none; }
            #fon-voice-interface .fon-site-nav-cta { min-height:42px; padding:0 14px; font-size:12px; }
            #fon-voice-interface .fon-landing-content { padding:32px 0 42px; }
            #fon-voice-interface .fon-landing-hero { grid-template-columns:1fr; gap:30px; padding:35px 0 45px; }
            #fon-voice-interface .fon-landing-copy h1 { max-width:12ch; font-size:clamp(47px,9vw,70px); }
            #fon-voice-interface .fon-landing-art { width:min(100%,520px); min-height:340px; justify-self:center; }
            #fon-voice-interface .fon-project-intro { grid-template-columns:1fr; gap:22px; padding:45px 0; }
            #fon-voice-interface .fon-facts { grid-template-columns:1fr; margin-top:4px; }
            #fon-voice-interface .fon-facts > div { min-height:auto; padding:18px 20px; }
            #fon-voice-interface .fon-facts > div + div { border-top:1px solid rgba(255,255,255,.1); border-left:0; }
            #fon-voice-interface .fon-approach { padding:48px 0; }
            #fon-voice-interface .fon-approach-cards { grid-template-columns:1fr; }
            #fon-voice-interface .fon-approach-card { min-height:0; }
            #fon-voice-interface .fon-approach-card h3 { margin-top:15px; }
            #fon-voice-interface .fon-vision-band { padding:28px; }
            #fon-voice-interface .fon-explore { padding:48px 0 35px; }
            #fon-voice-interface .fon-mode-cards { grid-template-columns:1fr; }
            #fon-voice-interface .fon-mode-card { min-height:190px; }
            #fon-voice-interface .fon-site-footer { justify-content:flex-start; padding:22px 0; }
          }
          @media (max-width:420px) {
            #fon-voice-interface #fon-landing { padding:0 17px; }
            #fon-voice-interface .fon-site-header { min-height:70px; }
            #fon-voice-interface .fon-site-mark { width:37px; height:37px; }
            #fon-voice-interface .fon-site-brand strong { font-size:15px; }
            #fon-voice-interface .fon-site-brand small { font-size:10px; }
            #fon-voice-interface .fon-site-nav-cta { min-height:39px; padding:0 11px; font-size:11px; }
            #fon-voice-interface .fon-landing-copy h1 { margin-top:18px; font-size:47px; }
            #fon-voice-interface .fon-landing-art { min-height:275px; }
            #fon-voice-interface .fon-art-core { width:145px; height:145px; }
            #fon-voice-interface .fon-art-word-one { left:7%; }
            #fon-voice-interface .fon-art-word-two { right:4%; }
            #fon-voice-interface .fon-art-caption { font-size:7px; letter-spacing:.1em; }
            #fon-voice-interface .fon-vision-band { padding:23px; }
            #fon-voice-interface .fon-responsibility { padding:17px; }
          }
        </style>
        """,
        elem_id="fon-voice-interface",
    )



web_app = FastAPI()


@web_app.get("/game")
async def fon_game_page():
    index_file = GAME_FRONTEND_DIST / "index.html"
    if not index_file.is_file():
        raise HTTPException(
            status_code=503,
            detail=(
                "Le front du jeu n'est pas construit. Exécute `npm ci && npm run build` "
                "dans tts_demo/frontend."
            ),
        )
    return FileResponse(index_file, media_type="text/html")


@web_app.get("/game-sw.js")
async def fon_game_service_worker():
    sw_file = GAME_FRONTEND_DIST / "game-sw.js"
    if not sw_file.is_file():
        raise HTTPException(status_code=404, detail="Service worker introuvable.")
    return FileResponse(sw_file, media_type="application/javascript")


def _voice_session_lock(session_id: str) -> asyncio.Lock:
    with VOICE_SESSION_GUARD:
        lock = VOICE_SESSION_LOCKS.get(session_id)
        if lock is None:
            lock = asyncio.Lock()
            VOICE_SESSION_LOCKS[session_id] = lock
        return lock


@web_app.post("/voice-turn")
async def voice_turn_request(request: Request):
    language = request.query_params.get("language", "")
    if language not in ("Français", "Fon"):
        raise HTTPException(
            status_code=400,
            detail="Choisis Français ou Fon comme langue parlée.",
        )
    try:
        session_id = str(uuid.UUID(request.headers.get("X-Conversation-Id", "")))
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Session vocale invalide.") from error

    try:
        client = OpenRouterClient.from_environment()
    except AssistantPipelineError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    audio_data = await request.body()
    if len(audio_data) > 12_000_000:
        raise HTTPException(status_code=413, detail="L'enregistrement est trop volumineux.")
    try:
        audio = read_wav_audio(audio_data)
    except AssistantASRError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    async def stream_transcription():
        event_queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def emit_event(event):
            loop.call_soon_threadsafe(
                event_queue.put_nowait,
                event,
            )

        async def run_voice_turn():
            try:
                async with _voice_session_lock(session_id):
                    history = VOICE_HISTORIES.get(session_id, [])
                    transcription, turn, response_audio = await run_in_threadpool(
                        process_voice_turn,
                        audio,
                        language,
                        history,
                        client,
                        emit_event,
                    )
                    VOICE_HISTORIES[session_id] = turn.history
                event_queue.put_nowait(
                    {
                        "type": "done",
                        "audio": encode_audio_wav(response_audio),
                        "fon_answer": turn.fon_answer,
                        "french_answer": turn.french_answer,
                    }
                )
            except (AssistantASRError, AssistantPipelineError, gr.Error) as error:
                event_queue.put_nowait({"type": "error", "message": str(error)})
            except Exception:
                LOGGER.exception("Unexpected voice assistant turn failure")
                event_queue.put_nowait(
                    {
                        "type": "error",
                        "message": (
                            "Une erreur inattendue a interrompu l'échange vocal. "
                            "Consulte le terminal du serveur pour le détail."
                        ),
                    }
                )

        task = asyncio.create_task(run_voice_turn())
        try:
            while True:
                event = await event_queue.get()
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                if event["type"] in ("done", "error"):
                    break
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    return StreamingResponse(
        stream_transcription(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@web_app.post("/training-examples")
async def save_training_example_request(request: Request):
    request_data = await request.body()
    if len(request_data) > MAX_TRAINING_REQUEST_BYTES:
        raise HTTPException(status_code=413, detail="La contribution est trop volumineuse.")
    try:
        payload = json.loads(request_data)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=400, detail="La contribution est invalide.") from error
    if not isinstance(payload, dict) or payload.get("consent") is not True:
        raise HTTPException(
            status_code=400,
            detail="Le consentement explicite est requis avant la sauvegarde.",
        )

    language = payload.get("language")
    asr_transcript = payload.get("asr_transcript")
    input_transcript = payload.get("input_transcript")
    assistant_fon_text_original = payload.get("assistant_fon_text_original")
    fon_answer = payload.get("assistant_fon_text")
    encoded_audio = payload.get("input_audio")
    speaker_id = sanitize_speaker_field(payload.get("speaker_id"))
    speaker_label = sanitize_speaker_field(payload.get("speaker_label"))
    if language not in ("Français", "Fon"):
        raise HTTPException(status_code=400, detail="La langue parlée est invalide.")
    if not isinstance(input_transcript, str) or not input_transcript.strip():
        raise HTTPException(status_code=400, detail="Corrige la transcription avant de sauvegarder.")
    if len(input_transcript) > 5_000:
        raise HTTPException(status_code=400, detail="La transcription est trop longue.")
    if not isinstance(asr_transcript, str) or not asr_transcript.strip():
        raise HTTPException(status_code=400, detail="La transcription ASR d'origine est manquante.")
    if len(asr_transcript) > 5_000:
        raise HTTPException(status_code=400, detail="La transcription ASR d'origine est trop longue.")
    if not isinstance(assistant_fon_text_original, str) or not assistant_fon_text_original.strip():
        raise HTTPException(status_code=400, detail="La réponse IA d'origine est manquante.")
    if len(assistant_fon_text_original) > 500:
        raise HTTPException(status_code=400, detail="La réponse IA d'origine est trop longue.")
    if not isinstance(fon_answer, str) or not fon_answer.strip():
        raise HTTPException(status_code=400, detail="La réponse en fon est obligatoire.")
    if len(fon_answer) > 500:
        raise HTTPException(status_code=400, detail="La réponse en fon dépasse 500 caractères.")
    if not isinstance(encoded_audio, str) or len(encoded_audio) > 16_000_000:
        raise HTTPException(status_code=400, detail="L'audio original est invalide.")
    try:
        input_audio = base64.b64decode(encoded_audio, validate=True)
    except (binascii.Error, ValueError) as error:
        raise HTTPException(status_code=400, detail="L'audio original est invalide.") from error
    if not input_audio or len(input_audio) > 12_000_000:
        raise HTTPException(status_code=413, detail="L'audio original est trop volumineux.")
    try:
        sample_rate, samples = await run_in_threadpool(read_wav_audio, input_audio)
        if samples.size == 0:
            raise AssistantASRError("L'enregistrement audio est vide.")
        if samples.shape[0] / sample_rate > 30:
            raise AssistantASRError("L'audio dépasse la limite de 30 secondes.")
    except AssistantASRError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    try:
        sample_id, assistant_audio = await run_in_threadpool(
            persist_training_example,
            input_audio,
            language,
            asr_transcript.strip(),
            input_transcript.strip(),
            assistant_fon_text_original.strip(),
            fon_answer.strip(),
            speaker_id,
            speaker_label,
        )
    except Exception as error:
        LOGGER.exception("Could not save a consented Fon training example")
        raise HTTPException(
            status_code=500,
            detail="Impossible d'enregistrer la contribution sur cet ordinateur.",
        ) from error

    return {"sample_id": sample_id, "assistant_audio": assistant_audio}


def sanitize_speaker_field(value, max_length=200):
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or len(value) > max_length:
        return None
    return value


async def parse_training_phrase_payload(request: Request):
    request_data = await request.body()
    if len(request_data) > MAX_TRAINING_REQUEST_BYTES:
        raise HTTPException(status_code=413, detail="La contribution est trop volumineuse.")
    try:
        payload = json.loads(request_data)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=400, detail="La contribution est invalide.") from error
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="La contribution est invalide.")
    return payload


def decode_training_phrase_audio(encoded_audio, field_name):
    if encoded_audio is None:
        return None
    if not isinstance(encoded_audio, str) or len(encoded_audio) > 16_000_000:
        raise HTTPException(status_code=400, detail=f"{field_name} invalide.")
    try:
        audio_data = base64.b64decode(encoded_audio, validate=True)
    except (binascii.Error, ValueError) as error:
        raise HTTPException(status_code=400, detail=f"{field_name} invalide.") from error
    if not audio_data or len(audio_data) > 12_000_000:
        raise HTTPException(status_code=413, detail=f"{field_name} trop volumineux.")
    try:
        sample_rate, samples = read_wav_audio(audio_data)
        if samples.size == 0:
            raise AssistantASRError("L'enregistrement audio est vide.")
        if samples.shape[0] / sample_rate > 30:
            raise AssistantASRError("L'audio dépasse la limite de 30 secondes.")
    except AssistantASRError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return audio_data


@web_app.post("/training-synthesis")
async def training_synthesis_request(request: Request):
    payload = await parse_training_phrase_payload(request)
    fon_text = payload.get("fon_text")
    if not isinstance(fon_text, str) or not fon_text.strip():
        raise HTTPException(status_code=400, detail="La traduction en fon est obligatoire.")
    if len(fon_text) > 500:
        raise HTTPException(status_code=400, detail="La traduction en fon dépasse 500 caractères.")
    try:
        audio = await run_in_threadpool(synthesize, fon_text.strip())
    except Exception as error:
        LOGGER.exception("Could not synthesize a Fon training phrase")
        raise HTTPException(
            status_code=500,
            detail="Impossible de générer la lecture en fon.",
        ) from error
    return {"audio": encode_audio_wav(audio)}


@web_app.post("/training-phrases")
async def save_training_phrase_request(request: Request):
    payload = await parse_training_phrase_payload(request)
    if payload.get("consent") is not True:
        raise HTTPException(
            status_code=400,
            detail="Le consentement explicite est requis avant la sauvegarde.",
        )
    french_text = payload.get("french_text")
    fon_text = payload.get("fon_text")
    if not isinstance(french_text, str) or not french_text.strip():
        raise HTTPException(status_code=400, detail="La phrase en français est obligatoire.")
    if len(french_text) > 500:
        raise HTTPException(status_code=400, detail="La phrase en français dépasse 500 caractères.")
    if not isinstance(fon_text, str) or not fon_text.strip():
        raise HTTPException(status_code=400, detail="La traduction en fon est obligatoire.")
    if len(fon_text) > 500:
        raise HTTPException(status_code=400, detail="La traduction en fon dépasse 500 caractères.")
    contribution_source = payload.get("source") or "free_collecte"
    if contribution_source not in ("game_mission", "free_collecte"):
        raise HTTPException(status_code=400, detail="La source de contribution est invalide.")
    mission_id = payload.get("mission_id")
    mission_title = payload.get("mission_title")
    if contribution_source == "game_mission":
        if (
            not isinstance(mission_id, str)
            or not mission_id.strip()
            or len(mission_id) > 80
        ):
            raise HTTPException(status_code=400, detail="L'identifiant de mission est invalide.")
        if (
            not isinstance(mission_title, str)
            or not mission_title.strip()
            or len(mission_title) > 120
        ):
            raise HTTPException(status_code=400, detail="Le titre de mission est invalide.")

    if payload.get("self_reviewed") is not True:
        raise HTTPException(
            status_code=400,
            detail="Merci de confirmer que la phrase et l'enregistrement sont corrects.",
        )

    human_audio = decode_training_phrase_audio(payload.get("human_audio"), "L'audio humain")
    if human_audio is None:
        raise HTTPException(
            status_code=400,
            detail="Un enregistrement vocal est requis pour cette contribution.",
        )
    synthesized_audio = decode_training_phrase_audio(
        payload.get("synthesized_audio"),
        "L'audio synthétisé",
    )
    speaker_id = sanitize_speaker_field(payload.get("speaker_id"))
    speaker_label = sanitize_speaker_field(payload.get("speaker_label"))
    try:
        sample_id, audio = await run_in_threadpool(
            persist_training_phrase,
            french_text.strip(),
            fon_text.strip(),
            human_audio,
            synthesized_audio,
            contribution_source,
            mission_id.strip() if isinstance(mission_id, str) else None,
            mission_title.strip() if isinstance(mission_title, str) else None,
            True,
            speaker_id,
            speaker_label,
            True,
        )
    except Exception as error:
        LOGGER.exception("Could not save a consented Fon phrase pair")
        raise HTTPException(
            status_code=500,
            detail="Impossible d'enregistrer la contribution sur cet ordinateur.",
        ) from error
    return {"sample_id": sample_id, "synthesized_audio": audio}


if GAME_FRONTEND_DIST.is_dir():
    web_app.mount(
        "/game-assets",
        StaticFiles(directory=GAME_FRONTEND_DIST),
        name="game-assets",
    )

try:
    web_app = gr.mount_gradio_app(web_app, demo, path="/", head=FONT_HEAD_TAGS)
except TypeError:
    # Older Gradio versions (<6, e.g. the gradio<5 pinned in requirements.txt)
    # don't accept `head` on mount_gradio_app; the Blocks(head=...) passed
    # above already covers font injection for those versions.
    web_app = gr.mount_gradio_app(web_app, demo, path="/")


if __name__ == "__main__":
    uvicorn.run(
        web_app,
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "7861")),
    )
