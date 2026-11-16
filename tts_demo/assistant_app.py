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


MICROPHONE_JS = r"""() => {
    const landing = document.querySelector("#fon-landing");
    const chatScreen = document.querySelector("#fon-chat-screen");
    const trainingScreen = document.querySelector("#fon-training-screen");
    const showScreen = (screen) => {
        landing.hidden = screen !== "home";
        chatScreen.hidden = screen !== "chat";
        trainingScreen.hidden = screen !== "training";
        window.scrollTo({ top: 0, behavior: "smooth" });
    };
    document.querySelectorAll("[data-open-chat]").forEach((button) => {
        button.addEventListener("click", () => showScreen("chat"));
    });
    document.querySelector("#fon-open-training")?.addEventListener(
        "click", () => showScreen("training")
    );
    document.querySelectorAll("[data-go-home]").forEach((button) => {
        button.addEventListener("click", () => showScreen("home"));
    });

    const startButton = document.querySelector("#fon-mic-start");
    const micLabel = document.querySelector("#fon-mic-label");
    const status = document.querySelector("#fon-mic-status");
    const transcript = document.querySelector("#fon-transcript");
    const answer = document.querySelector("#fon-answer");
    const guide = document.querySelector("#fon-guide");
    const replayButton = document.querySelector("#fon-replay");
    const responseAudio = document.querySelector("#fon-response-audio");
    const language = document.querySelector("#source-language");
    const contribution = document.querySelector("#fon-contribution");
    const consent = document.querySelector("#fon-collection-consent");
    const saveButton = document.querySelector("#fon-save-contribution");
    const contributionStatus = document.querySelector("#fon-contribution-status");
    const frenchText = document.querySelector("#training-french");
    const fonText = document.querySelector("#training-fon");
    const trainingPlayButton = document.querySelector("#training-play");
    const trainingRecordButton = document.querySelector("#training-record");
    const trainingRecordStatus = document.querySelector("#training-record-status");
    const trainingAudio = document.querySelector("#training-audio");
    const trainingConsent = document.querySelector("#training-consent");
    const trainingSaveButton = document.querySelector("#training-save");
    const trainingSaveStatus = document.querySelector("#training-save-status");
    if (!startButton || !micLabel || !status || !transcript || !answer || !guide ||
        !replayButton || !responseAudio || !language || !contribution ||
        !consent || !saveButton || !contributionStatus || !frenchText || !fonText ||
        !trainingPlayButton || !trainingRecordButton || !trainingRecordStatus ||
        !trainingAudio || !trainingConsent || !trainingSaveButton || !trainingSaveStatus) return;

    let stream;
    let audioContext;
    let source;
    let processor;
    let silentOutput;
    let chunks = [];
    let progressTimer;
    let recordingStartedAt;
    let lastSpeechAt;
    let hasDetectedSpeech = false;
    let recordingActive = false;
    let stageStartedAt;
    let stageTimer;
    let responseAudioUrl;
    let lastInputWav;
    let rawInputTranscript = "";
    let rawAssistantFonText = "";
    let contributionSaved = false;
    let trainingStream;
    let trainingAudioContext;
    let trainingSource;
    let trainingProcessor;
    let trainingChunks = [];
    let trainingHumanAudio;
    let trainingSynthesizedAudio;
    let trainingAudioUrl;
    let trainingRecording = false;
    let trainingSaveInProgress = false;
    let trainingPhraseSaved = false;
    const conversationId = sessionStorage.fonConversationId ||
        (sessionStorage.fonConversationId = crypto.randomUUID());

    const progressTrack = document.querySelector("#fon-progress-track");
    const progressFill = document.querySelector("#fon-progress-fill");
    const setStatus = (message, kind = "info") => {
        status.textContent = message;
        status.dataset.state = kind;
    };
    const setGuideState = (state) => {
        guide.dataset.state = state;
    };
    const setMicLabel = (label, state) => {
        micLabel.textContent = label;
        startButton.dataset.state = state;
        startButton.setAttribute("aria-label", label);
    };
    const setContributionVisible = (visible) => {
        contribution.hidden = !visible;
        if (!visible) {
            contributionSaved = false;
            consent.checked = false;
            saveButton.disabled = true;
            saveButton.textContent = "Enregistrer ma contribution";
            contributionStatus.textContent = "";
            contributionStatus.dataset.state = "info";
        }
    };
    const setProgress = (mode, value = 0) => {
        progressTrack.dataset.mode = mode;
        if (mode === "indeterminate" || mode === "error" || mode === "hidden") {
            progressTrack.removeAttribute("aria-valuenow");
        } else {
            progressTrack.setAttribute("aria-valuenow", String(value));
        }
        progressFill.style.width = `${value}%`;
    };
    const stopProgressTimer = () => {
        clearInterval(progressTimer);
        progressTimer = undefined;
    };
    const stopStageTimer = () => {
        clearInterval(stageTimer);
        stageTimer = undefined;
    };
    const stopTracks = () => {
        if (stream) stream.getTracks().forEach((track) => track.stop());
        stream = undefined;
    };
    const updateStage = (message) => {
        stopStageTimer();
        setStatus(message);
        setGuideState("processing");
        const stages = [
            ["Chargement du modèle de reconnaissance", "Chargement du modèle"],
            ["Chargement de l'adaptateur de langue", "Chargement de l'adaptateur"],
            ["Analyse de la parole en cours", "Analyse de la parole"],
            ["Finalisation du texte reconnu", "Finalisation du texte"],
            ["Génération de la réponse", "Génération de la réponse"],
            ["Synthèse vocale de la réponse", "Synthèse de la voix"],
        ];
        const activeStage = stages.find(([prefix]) => message.startsWith(prefix));
        if (!activeStage) return;

        stageStartedAt = performance.now();
        stageTimer = setInterval(() => {
            const elapsedSeconds = Math.floor(
                (performance.now() - stageStartedAt) / 1000
            );
            setStatus(`${activeStage[1]}… (${elapsedSeconds} s)`);
        }, 1000);
    };
    const encodeWav = (samples, sampleRate) => {
        const frameCount = samples.reduce((total, chunk) => total + chunk.length, 0);
        const buffer = new ArrayBuffer(44 + frameCount * 2);
        const view = new DataView(buffer);
        const writeText = (offset, text) => {
            for (let index = 0; index < text.length; index += 1) {
                view.setUint8(offset + index, text.charCodeAt(index));
            }
        };
        writeText(0, "RIFF");
        view.setUint32(4, buffer.byteLength - 8, true);
        writeText(8, "WAVE");
        writeText(12, "fmt ");
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true);
        view.setUint16(22, 1, true);
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, sampleRate * 2, true);
        view.setUint16(32, 2, true);
        view.setUint16(34, 16, true);
        writeText(36, "data");
        view.setUint32(40, frameCount * 2, true);
        let offset = 44;
        for (const chunk of samples) {
            for (const sample of chunk) {
                const clipped = Math.max(-1, Math.min(1, sample));
                view.setInt16(
                    offset,
                    clipped < 0 ? clipped * 32768 : clipped * 32767,
                    true
                );
                offset += 2;
            }
        }
        return new Blob([buffer], { type: "audio/wav" });
    };
    const encodeBase64 = async (blob) => {
        const bytes = new Uint8Array(await blob.arrayBuffer());
        let binary = "";
        for (let offset = 0; offset < bytes.length; offset += 0x8000) {
            binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
        }
        return btoa(binary);
    };
    const setTrainingStatus = (element, message, kind = "info") => {
        element.textContent = message;
        element.dataset.state = kind;
    };
    const stopTrainingRecording = async () => {
        if (!trainingRecording) return;
        trainingRecording = false;
        trainingRecordButton.disabled = true;
        try {
            trainingProcessor.disconnect();
            trainingSource.disconnect();
            const sampleRate = trainingAudioContext.sampleRate;
            await trainingAudioContext.close();
            trainingAudioContext = undefined;
            trainingStream.getTracks().forEach((track) => track.stop());
            trainingStream = undefined;
            trainingHumanAudio = encodeWav(trainingChunks, sampleRate);
            trainingChunks = [];
            trainingRecordButton.textContent = "● Refaire mon enregistrement";
            setTrainingStatus(trainingRecordStatus, "Ta prononciation est prête à être enregistrée avec ton consentement.", "success");
        } catch (error) {
            setTrainingStatus(trainingRecordStatus, `Erreur d'enregistrement : ${error.message}`, "error");
        } finally {
            trainingRecordButton.disabled = false;
        }
    };
    trainingPlayButton.addEventListener("click", async () => {
        const text = fonText.value.trim();
        if (!text) {
            setTrainingStatus(trainingRecordStatus, "Saisis d'abord une traduction en fon.", "error");
            fonText.focus();
            return;
        }
        trainingPlayButton.disabled = true;
        trainingPlayButton.textContent = "Synthèse en cours…";
        setTrainingStatus(trainingRecordStatus, "Préparation de la lecture…");
        try {
            const response = await fetch("/training-synthesis", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ fon_text: text }),
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.detail || "La synthèse n'a pas pu être générée.");
            trainingSynthesizedAudio = result.audio;
            const audioBytes = Uint8Array.from(
                atob(result.audio), (character) => character.charCodeAt(0)
            );
            if (trainingAudioUrl) URL.revokeObjectURL(trainingAudioUrl);
            trainingAudioUrl = URL.createObjectURL(new Blob([audioBytes], { type: "audio/wav" }));
            trainingAudio.src = trainingAudioUrl;
            trainingAudio.hidden = false;
            await trainingAudio.play();
            setTrainingStatus(trainingRecordStatus, "Lecture de la traduction en fon.");
        } catch (error) {
            setTrainingStatus(trainingRecordStatus, `Erreur : ${error.message}`, "error");
        } finally {
            trainingPlayButton.disabled = false;
            trainingPlayButton.textContent = "▶ Écouter la voix de l'IA";
        }
    });
    trainingRecordButton.addEventListener("click", async () => {
        if (trainingRecording) {
            await stopTrainingRecording();
            return;
        }
        trainingRecordButton.disabled = true;
        setTrainingStatus(trainingRecordStatus, "Connexion au microphone…");
        try {
            trainingStream = await navigator.mediaDevices.getUserMedia({
                audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
            });
            trainingAudioContext = new AudioContext();
            await trainingAudioContext.resume();
            trainingSource = trainingAudioContext.createMediaStreamSource(trainingStream);
            trainingProcessor = trainingAudioContext.createScriptProcessor(4096, 1, 1);
            const silentOutput = trainingAudioContext.createGain();
            silentOutput.gain.value = 0;
            trainingChunks = [];
            trainingHumanAudio = undefined;
            trainingProcessor.onaudioprocess = (event) => {
                trainingChunks.push(new Float32Array(event.inputBuffer.getChannelData(0)));
            };
            trainingSource.connect(trainingProcessor);
            trainingProcessor.connect(silentOutput);
            silentOutput.connect(trainingAudioContext.destination);
            trainingRecording = true;
            trainingRecordButton.textContent = "■ Terminer l'enregistrement";
            setTrainingStatus(trainingRecordStatus, "Enregistrement… lis la phrase en fon, puis termine l'enregistrement.");
            setTimeout(() => {
                if (trainingRecording) {
                    setTrainingStatus(trainingRecordStatus, "Limite de 30 secondes atteinte. Finalisation de l'enregistrement.");
                    void stopTrainingRecording();
                }
            }, 30_000);
        } catch (error) {
            if (trainingStream) trainingStream.getTracks().forEach((track) => track.stop());
            trainingStream = undefined;
            if (trainingAudioContext) await trainingAudioContext.close();
            trainingAudioContext = undefined;
            setTrainingStatus(trainingRecordStatus, `Impossible d'accéder au micro : ${error.message}`, "error");
        } finally {
            trainingRecordButton.disabled = false;
        }
    });
    trainingConsent.addEventListener("change", () => {
        trainingSaveButton.disabled =
            !trainingConsent.checked || trainingSaveInProgress || trainingPhraseSaved;
    });
    for (const field of [frenchText, fonText]) {
        field.addEventListener("input", () => {
            trainingSaveStatus.textContent = "";
            trainingPhraseSaved = false;
            trainingSaveButton.textContent = "Enregistrer cette contribution";
            trainingSaveButton.disabled = !trainingConsent.checked || trainingSaveInProgress;
            trainingHumanAudio = undefined;
            trainingRecordButton.textContent = "● Enregistrer ma voix";
            if (field === fonText) {
                trainingSynthesizedAudio = undefined;
                trainingAudio.pause();
                trainingAudio.removeAttribute("src");
                trainingAudio.hidden = true;
                setTrainingStatus(
                    trainingRecordStatus,
                    "La traduction a changé. Génère sa lecture ou enregistre à nouveau ta prononciation."
                );
            } else {
                setTrainingStatus(
                    trainingRecordStatus,
                    "La phrase française a changé. Enregistre à nouveau ta prononciation si tu souhaites l'associer à ces textes."
                );
            }
        });
    }
    trainingSaveButton.addEventListener("click", async () => {
        const french = frenchText.value.trim();
        const fon = fonText.value.trim();
        if (!trainingConsent.checked || trainingSaveInProgress) return;
        if (!french || !fon) {
            setTrainingStatus(trainingSaveStatus, "Renseigne la phrase française et sa traduction en fon.", "error");
            return;
        }
        trainingSaveInProgress = true;
        trainingSaveButton.disabled = true;
        setTrainingStatus(trainingSaveStatus, "Enregistrement local de la contribution…");
        try {
            const response = await fetch("/training-phrases", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    consent: trainingConsent.checked,
                    french_text: french,
                    fon_text: fon,
                    human_audio: trainingHumanAudio ? await encodeBase64(trainingHumanAudio) : null,
                    synthesized_audio: trainingSynthesizedAudio || null,
                }),
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.detail || "La contribution n'a pas pu être enregistrée.");
            trainingPhraseSaved = true;
            setTrainingStatus(trainingSaveStatus, `Contribution enregistrée sur cet ordinateur (référence ${result.sample_id}).`, "success");
            trainingSaveButton.textContent = "Contribution enregistrée";
            const bytes = Uint8Array.from(atob(result.synthesized_audio), (character) => character.charCodeAt(0));
            if (trainingAudioUrl) URL.revokeObjectURL(trainingAudioUrl);
            trainingAudioUrl = URL.createObjectURL(new Blob([bytes], { type: "audio/wav" }));
            trainingAudio.src = trainingAudioUrl;
            trainingAudio.hidden = false;
        } catch (error) {
            setTrainingStatus(trainingSaveStatus, `Erreur : ${error.message}`, "error");
        } finally {
            trainingSaveInProgress = false;
            trainingSaveButton.disabled =
                !trainingConsent.checked || trainingPhraseSaved;
        }
    });
    const playResponse = async () => {
        replayButton.hidden = true;
        setGuideState("speaking");
        setMicLabel("Je parle…", "speaking");
        try {
            await responseAudio.play();
            setStatus("Réponse en fon en cours…");
        } catch (_error) {
            setGuideState("idle");
            setMicLabel("Parler", "idle");
            replayButton.hidden = false;
            startButton.disabled = false;
            setStatus("La réponse est prête. Clique sur « Écouter la réponse ».");
        }
    };
    replayButton.addEventListener("click", playResponse);
    consent.addEventListener("change", () => {
        saveButton.disabled = !consent.checked || contributionSaved;
    });
    saveButton.addEventListener("click", async () => {
        if (!consent.checked || !lastInputWav || contributionSaved) return;
        const correctedTranscript = transcript.value.trim();
        const correctedAnswer = answer.value.trim();
        if (!correctedTranscript || !correctedAnswer) {
            contributionStatus.textContent =
                "La transcription et la réponse en fon doivent toutes les deux être renseignées.";
            contributionStatus.dataset.state = "error";
            return;
        }

        saveButton.disabled = true;
        contributionStatus.textContent = "Enregistrement local de la contribution…";
        contributionStatus.dataset.state = "info";
        try {
            const response = await fetch("/training-examples", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    consent: consent.checked,
                    language: language.value,
                    input_audio: await encodeBase64(lastInputWav),
                    asr_transcript: rawInputTranscript,
                    input_transcript: correctedTranscript,
                    assistant_fon_text_original: rawAssistantFonText,
                    assistant_fon_text: correctedAnswer,
                }),
            });
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.detail || "La contribution n'a pas pu être enregistrée.");
            }

            contributionSaved = true;
            saveButton.textContent = "Contribution enregistrée";
            contributionStatus.textContent =
                `Enregistrée sur cet ordinateur (référence ${result.sample_id}).`;
            contributionStatus.dataset.state = "success";

            const audioBytes = Uint8Array.from(
                atob(result.assistant_audio),
                (character) => character.charCodeAt(0)
            );
            if (responseAudioUrl) URL.revokeObjectURL(responseAudioUrl);
            responseAudioUrl = URL.createObjectURL(
                new Blob([audioBytes], { type: "audio/wav" })
            );
            responseAudio.src = responseAudioUrl;
            replayButton.hidden = false;
        } catch (error) {
            saveButton.disabled = false;
            contributionStatus.textContent = `Erreur : ${error.message}`;
            contributionStatus.dataset.state = "error";
        }
    });
    responseAudio.addEventListener("play", () => {
        setGuideState("speaking");
        setMicLabel("Je parle…", "speaking");
    });
    responseAudio.addEventListener("ended", () => {
        startButton.disabled = false;
        setMicLabel("Parler", "idle");
        setGuideState("idle");
        setStatus("À toi de parler.");
    });

    const stopRecording = async () => {
        if (!recordingActive) return;
        recordingActive = false;
        startButton.disabled = true;
        stopProgressTimer();
        setMicLabel("Envoi…", "processing");
        setGuideState("processing");
        try {
            processor.disconnect();
            source.disconnect();
            silentOutput.disconnect();
            const sampleRate = audioContext.sampleRate;
            await audioContext.close();
            audioContext = undefined;
            stopTracks();

            if (!hasDetectedSpeech) {
                chunks = [];
                startButton.disabled = false;
                setMicLabel("Parler", "idle");
                setGuideState("idle");
                setProgress("hidden");
                setStatus("Je n'ai pas détecté de parole. Réessaie en parlant près du micro.", "error");
                return;
            }

            const wav = encodeWav(chunks, sampleRate);
            chunks = [];
            lastInputWav = wav;
            setProgress("indeterminate");
            setStatus("Transcription locale en cours…");
            const response = await fetch(
                `/voice-turn?language=${encodeURIComponent(language.value)}`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "audio/wav",
                        "X-Conversation-Id": conversationId,
                    },
                    body: wav,
                }
            );
            if (!response.ok) {
                const errorResult = await response.json();
                throw new Error(errorResult.detail || "L'échange vocal a échoué.");
            }
            if (!response.body) throw new Error("Le serveur n'a pas démarré l'échange vocal.");

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";
            let completedTurn = false;
            const handleEvent = (event) => {
                if (event.type === "progress") {
                    updateStage(event.message);
                } else if (event.type === "transcript") {
                    rawInputTranscript = event.text;
                    transcript.value = event.text;
                    updateStage("Transcription terminée. Envoi au modèle…");
                } else if (event.type === "done") {
                    completedTurn = true;
                    stopStageTimer();
                    rawAssistantFonText = event.fon_answer;
                    answer.value = event.fon_answer;
                    const audioBytes = Uint8Array.from(
                        atob(event.audio), (character) => character.charCodeAt(0)
                    );
                    responseAudioUrl = URL.createObjectURL(
                        new Blob([audioBytes], { type: "audio/wav" })
                    );
                    responseAudio.src = responseAudioUrl;
                    setProgress("complete", 100);
                    setContributionVisible(true);
                    playResponse();
                } else if (event.type === "error") {
                    throw new Error(event.message);
                }
            };
            while (true) {
                const { value, done } = await reader.read();
                buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
                const messages = buffer.split("\n\n");
                buffer = messages.pop() || "";
                for (const message of messages) {
                    const dataLine = message.split("\n").find((line) => line.startsWith("data:"));
                    if (dataLine) handleEvent(JSON.parse(dataLine.slice(5).trim()));
                }
                if (done) break;
            }
            if (buffer.startsWith("data:")) handleEvent(JSON.parse(buffer.slice(5).trim()));
            if (!completedTurn) throw new Error("L'assistant n'a pas terminé sa réponse.");
        } catch (error) {
            stopStageTimer();
            setGuideState("idle");
            setMicLabel("Parler", "idle");
            setProgress("error");
            setStatus(`Erreur : ${error.message}`, "error");
            startButton.disabled = false;
        } finally {
            stopStageTimer();
        }
    };

    startButton.addEventListener("click", async () => {
        if (recordingActive) {
            await stopRecording();
            return;
        }
        startButton.disabled = true;
        responseAudio.pause();
        setGuideState("idle");
        setMicLabel("Connexion…", "processing");
        setContributionVisible(false);
        lastInputWav = undefined;
        rawInputTranscript = "";
        rawAssistantFonText = "";
        if (responseAudioUrl) URL.revokeObjectURL(responseAudioUrl);
        responseAudioUrl = undefined;
        responseAudio.removeAttribute("src");
        setProgress("hidden");
        transcript.value = "";
        answer.value = "";
        transcript.placeholder = "La transcription reconnue apparaîtra ici.";
        answer.placeholder = "La réponse en fon apparaîtra ici.";
        contributionStatus.textContent = "";
        setStatus("Connexion au microphone…");
        try {
            stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                },
            });
            audioContext = new AudioContext();
            await audioContext.resume();
            source = audioContext.createMediaStreamSource(stream);
            processor = audioContext.createScriptProcessor(4096, 1, 1);
            silentOutput = audioContext.createGain();
            silentOutput.gain.value = 0;
            chunks = [];
            processor.onaudioprocess = (event) => {
                const samples = new Float32Array(event.inputBuffer.getChannelData(0));
                chunks.push(samples);
                let energy = 0;
                for (const sample of samples) energy += sample * sample;
                const rms = Math.sqrt(energy / samples.length);
                if (rms >= 0.018) {
                    if (!hasDetectedSpeech) {
                        setStatus("Parole détectée. L'envoi se fera après une courte pause.");
                    }
                    hasDetectedSpeech = true;
                    lastSpeechAt = performance.now();
                }
            };
            source.connect(processor);
            processor.connect(silentOutput);
            silentOutput.connect(audioContext.destination);
            recordingStartedAt = performance.now();
            lastSpeechAt = undefined;
            hasDetectedSpeech = false;
            recordingActive = true;
            setProgress("recording", 0);
            setGuideState("listening");
            setMicLabel("Je t'écoute…", "listening");
            startButton.disabled = false;
            setStatus("Parle normalement. J'enverrai après 1,5 seconde de silence.");
            progressTimer = setInterval(() => {
                const elapsedSeconds = Math.min(
                    30,
                    (performance.now() - recordingStartedAt) / 1000
                );
                const elapsedPercent = (elapsedSeconds / 30) * 100;
                setProgress("recording", elapsedPercent);
                if (
                    hasDetectedSpeech &&
                    lastSpeechAt &&
                    performance.now() - lastSpeechAt >= 1500
                ) {
                    setStatus("Silence détecté. Envoi de ta phrase…");
                    void stopRecording();
                    return;
                }
                if (elapsedSeconds >= 30) {
                    setStatus("Limite de 30 secondes atteinte. Envoi de ta phrase…");
                    void stopRecording();
                    return;
                }
            }, 100);
        } catch (error) {
            stopProgressTimer();
            stopTracks();
            if (audioContext) await audioContext.close();
            audioContext = undefined;
            startButton.disabled = false;
            setMicLabel("Parler", "idle");
            setGuideState("idle");
            setProgress("hidden");
            setStatus(`Impossible d'accéder au micro : ${error.message}`, "error");
        }
    });
}"""


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
        "input_language": language,
        "asr_transcript": asr_transcript,
        "input_transcript": input_transcript,
        "input_audio_file": "input_audio.wav",
        "input_audio_role": "user_recording_for_asr",
        "assistant_fon_text_original": assistant_fon_text_original,
        "assistant_fon_text": fon_answer,
        "assistant_audio_file": "assistant_audio.wav",
        "assistant_audio_role": "ai_synthesized_for_quality_review_not_human_tts_target",
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
    contribution_source="training",
    mission_id=None,
    mission_title=None,
    generate_synthesis=True,
):
    phrase_dir = DATASET_DIR / "phrase-pairs"
    phrase_dir.mkdir(parents=True, exist_ok=True)
    sample_id = str(uuid.uuid4())
    if synthesized_audio is None and generate_synthesis:
        synthesized_audio = base64.b64decode(encode_audio_wav(synthesize(fon_text)))
    human_audio_role = None
    if human_audio:
        human_audio_role = (
            "human_recording_for_review"
            if contribution_source == "game"
            else "human_tts_training_target"
        )
    metadata = {
        "schema_version": 1,
        "sample_id": sample_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "consent": True,
        "contribution_source": contribution_source,
        "review_status": "unreviewed",
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
        "human_audio_file": "fon_human_reading.wav" if human_audio else None,
        "human_audio_role": human_audio_role,
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


with gr.Blocks(title="Le carnet des voix — aventure en fon") as demo:
    gr.HTML(
        """
        <div id="fon-landing" class="fon-landing">
          <div class="fon-landing-brand">
            <span class="fon-brand-mark" aria-hidden="true">F</span>
            <div><strong>Le carnet des voix</strong><span>Bénin · une aventure en fon</span></div>
          </div>
          <div class="fon-landing-content">
            <section class="fon-landing-hero">
              <div class="fon-landing-copy">
                <span class="fon-eyebrow">Une aventure autour du fon</span>
                <h1>Fais entendre ta voix.</h1>
                <p>Joue, échange avec l'assistant ou contribue à faire grandir les ressources en fon.</p>
              </div>
              <div class="fon-landing-art" aria-hidden="true">
                <span class="fon-art-sun"></span>
                <span class="fon-art-hill fon-art-hill-back"></span>
                <span class="fon-art-hill fon-art-hill-front"></span>
                <div class="fon-art-tower">
                  <span class="fon-art-tower-mast"></span>
                  <span class="fon-art-tower-cross"></span>
                  <span class="fon-art-wave fon-art-wave-one"></span>
                  <span class="fon-art-wave fon-art-wave-two"></span>
                </div>
                <div class="fon-art-station">
                  <span class="fon-art-sign">FON FM</span>
                  <span class="fon-art-window"></span>
                  <span class="fon-art-door"></span>
                </div>
                <div class="fon-art-radio">
                  <span>EN DIRECT</span>
                  <div class="fon-art-equalizer">
                    <i></i><i></i><i></i><i></i><i></i><i></i><i></i>
                  </div>
                </div>
                <span class="fon-art-caption">UN SIGNAL · TOUT UN QUARTIER</span>
              </div>
            </section>
            <div class="fon-mode-heading">
              <div>
                <span class="fon-eyebrow">À toi de choisir</span>
                <h2>Choisis ton parcours</h2>
              </div>
              <span class="fon-mode-count">3 façons d'explorer</span>
            </div>
            <div class="fon-mode-cards">
              <a class="fon-mode-card fon-game-card" href="/game">
                <span class="fon-card-topline"><span class="fon-mode-icon">♫</span><span class="fon-card-tag">Chapitre pilote</span></span>
                <strong>Explorer Le carnet des voix</strong>
                <span>Prépare des phrases pour une radio fictive et découvre des repères sourcés sur l'histoire du Bénin.</span>
                <span class="fon-mode-action">Lancer l'aventure <b aria-hidden="true">→</b></span>
              </a>
              <button id="fon-open-chat" class="fon-mode-card" data-open-chat type="button">
                <span class="fon-card-topline"><span class="fon-mode-icon" aria-hidden="true">◉</span><span class="fon-card-tag">Conversation</span></span>
                <strong>Discuter avec l'IA</strong>
                <span>Parle naturellement et reçois une réponse orale en fon.</span>
                <span class="fon-mode-action">Commencer la discussion <b aria-hidden="true">→</b></span>
              </button>
              <button id="fon-open-training" class="fon-mode-card" type="button">
                <span class="fon-card-topline"><span class="fon-mode-icon fon-mode-icon-training" aria-hidden="true">Aa</span><span class="fon-card-tag">Contribution libre</span></span>
                <strong>Contribuer à l'entraînement</strong>
                <span>Ajoute une phrase français/fon et enregistre sa prononciation.</span>
                <span class="fon-mode-action">Ajouter une phrase <b aria-hidden="true">→</b></span>
              </button>
            </div>
            <p class="fon-landing-note">Tes contributions restent sur le serveur qui héberge le prototype et ne sont enregistrées qu'avec ton accord.</p>
          </div>
          <nav class="fon-home-nav" aria-label="Navigation principale">
            <a class="fon-home-nav-item" href="/game">
              <span aria-hidden="true">◇</span>
              <span>Histoire</span>
            </a>
            <button class="fon-home-nav-item" data-open-chat type="button">
              <span aria-hidden="true">◉</span>
              <span>Ma voix</span>
            </button>
            <button class="fon-home-nav-item is-active" data-go-home type="button" aria-current="page">
              <span aria-hidden="true">⌂</span>
              <span>Accueil</span>
            </button>
          </nav>
        </div>
        <div id="fon-chat-screen" hidden>
        <div class="fon-page">
          <header class="fon-header">
            <div class="fon-brand">
              <span class="fon-brand-mark" aria-hidden="true">F</span>
              <div><strong>Assistant vocal</strong><span>Parlons en fon</span></div>
            </div>
            <button class="fon-back-button" data-go-home type="button">← Accueil</button>
            <label class="fon-language">
              <span>Langue</span>
              <select id="source-language" aria-label="Langue parlée">
                <option value="Français" selected>Français</option>
                <option value="Fon">Fon</option>
              </select>
            </label>
          </header>
          <main class="fon-layout">
            <section class="fon-hero" aria-label="Assistant vocal">
              <div class="fon-guide-halo">
                <div id="fon-guide" data-state="idle" role="img"
                  aria-label="Guide souriant, un homme en tenue colorée qui vous accueille">
                  <svg viewBox="0 0 240 330" aria-hidden="true">
                    <ellipse cx="119" cy="317" rx="88" ry="9" fill="#101435" opacity=".18"/>
                    <path d="M39 319c5-43 19-69 49-82l30-8 31 8c29 11 47 39 53 82Z" fill="#1c2670"/>
                    <path d="M49 285l17-18 17 18-17 18Zm59-25 13-14 14 14-14 14Zm54 28 17-18 17 18-17 18Z" fill="#d3234b"/>
                    <circle cx="92" cy="280" r="7" fill="#f5b800"/><circle cx="145" cy="302" r="7" fill="#0f8a4f"/>
                    <circle cx="188" cy="274" r="6" fill="#f5b800"/><circle cx="105" cy="311" r="5" fill="#0f8a4f"/>
                    <path d="M97 216h45v38q-21 17-45 0Z" fill="#75482e"/>
                    <path d="M55 250q23-19 48-23l17 20 17-20q28 4 52 23l-22 26-9-13v56H57v-56l-10 13-16-16Z" fill="#f5b800"/>
                    <path d="M61 253q19-16 40-20l19 20 19-20q23 4 42 20l-19 23-10-12v52H71v-52l-10 12-12-13Z" fill="#1c2670"/>
                    <path d="m88 244 9 10-10 10-10-10Zm59 24 9 10-10 10-10-10Zm-45 27 7 8-8 8-8-8Z" fill="#d3234b"/>
                    <circle cx="125" cy="241" r="4" fill="#f5b800"/><circle cx="174" cy="250" r="4" fill="#f5b800"/>
                    <path d="M104 239q21 19 42 0" fill="none" stroke="#f5b800" stroke-width="4" stroke-linecap="round"/>
                    <circle cx="125" cy="257" r="4" fill="#f5b800"/>
                    <path d="M50 250q-15 18-17 38" fill="none" stroke="#75482e" stroke-width="16" stroke-linecap="round"/>
                    <circle cx="32" cy="291" r="9" fill="#75482e"/>
                    <g class="fon-guide-arm">
                      <path d="M172 246q18-20 21-45l4-29" fill="none" stroke="#75482e" stroke-width="17" stroke-linecap="round" stroke-linejoin="round"/>
                      <path d="M197 177q-8-2-8-10l1-17q0-5 4-5t4 5l1 10 2-17q1-5 5-4 4 0 3 6l-1 16 4-12q2-5 6-3 4 2 2 7l-4 15q-3 13-15 14Z" fill="#75482e"/>
                      <path d="M193 168q7 5 14 2" fill="none" stroke="#603a28" stroke-width="2" stroke-linecap="round"/>
                    </g>
                    <path d="M67 143Q56 111 64 84Q70 52 102 53Q144 43 171 64Q190 83 181 143L169 125Q163 100 139 94Q110 85 85 107L77 131Z" fill="#241713"/>
                    <ellipse cx="66" cy="157" rx="10" ry="15" fill="#75482e"/>
                    <ellipse cx="181" cy="157" rx="10" ry="15" fill="#75482e"/>
                    <ellipse cx="124" cy="151" rx="56" ry="67" fill="#8a5635"/>
                    <circle cx="66" cy="174" r="8" fill="#f5b800"/><circle cx="182" cy="174" r="8" fill="#f5b800"/>
                    <ellipse cx="101" cy="166" rx="13" ry="8" fill="#d96f68" opacity=".48"/>
                    <ellipse cx="148" cy="166" rx="13" ry="8" fill="#d96f68" opacity=".48"/>
                    <path d="M91 135q12-9 23 0m16 0q12-9 23 0" fill="none" stroke="#241713" stroke-width="5" stroke-linecap="round"/>
                    <ellipse cx="104" cy="148" rx="8" ry="10" fill="#fff"/><ellipse cx="141" cy="148" rx="8" ry="10" fill="#fff"/>
                    <circle cx="106" cy="149" r="4.5" fill="#241713"/><circle cx="139" cy="149" r="4.5" fill="#241713"/>
                    <circle cx="107" cy="147" r="1.5" fill="#fff"/><circle cx="140" cy="147" r="1.5" fill="#fff"/>
                    <path d="M123 151q-3 15 3 17" fill="none" stroke="#603a28" stroke-width="3" stroke-linecap="round"/>
                    <path d="M101 175q11-8 22 0 6-7 12 0 11-8 22 0l-4 7q-9 4-17-2-7 6-17 2-9 4-17-2Z" fill="#30201c"/>
                    <g class="fon-guide-mouth">
                      <path d="M108 190q16 13 32 0-4 15-16 15t-16-15Z" fill="#54251f"/>
                      <path d="M111 191q13 8 26 0" fill="none" stroke="#f3b4a1" stroke-width="3" stroke-linecap="round"/>
                    </g>
                    <path d="M75 85q9-22 29-24m8-3 5-1m11 1 5 1m11 4 4 3" fill="none" stroke="#3b241d" stroke-width="5" stroke-linecap="round"/>
                    <circle cx="84" cy="71" r="3" fill="#3b241d"/><circle cx="98" cy="61" r="3" fill="#3b241d"/>
                  </svg>
                </div>
              </div>
              <button id="fon-mic-start" type="button" data-state="idle">
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <rect x="9" y="2" width="6" height="12" rx="3" fill="currentColor"/>
                  <path d="M5 11a7 7 0 0 0 14 0M12 18v4m-4 0h8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
                <span id="fon-mic-label">Parler</span>
              </button>
              <div id="fon-progress-track" data-mode="hidden" role="progressbar"
                aria-label="Progression de l'enregistrement et de la réponse"
                aria-valuemin="0" aria-valuemax="100" aria-valuenow="0">
                <div id="fon-progress-fill"></div>
              </div>
              <p id="fon-mic-status" role="status" aria-live="polite">
                Appuie sur Parler pour commencer.
              </p>
              <button id="fon-replay" type="button" hidden>Écouter la réponse</button>
            </section>
            <section class="fon-transcript-panel" aria-live="polite">
              <div class="fon-transcript-heading">
                <span class="fon-transcript-icon" aria-hidden="true">Aa</span>
                <div><h1>Ta parole</h1><p>Corrige la transcription si nécessaire</p></div>
              </div>
              <label class="fon-field">
                <span>Transcription reconnue</span>
                <textarea id="fon-transcript" rows="3"
                  placeholder="Ta phrase apparaîtra ici après la reconnaissance."></textarea>
              </label>
              <label class="fon-field">
                <span>Réponse de l'assistant en fon</span>
                <textarea id="fon-answer" rows="4"
                  placeholder="La réponse en fon apparaîtra ici. Tu peux la corriger."></textarea>
              </label>
              <audio id="fon-response-audio" controls preload="metadata"></audio>
              <div id="fon-contribution" hidden>
                <label class="fon-consent">
                  <input id="fon-collection-consent" type="checkbox">
                  <span>J'accepte de sauvegarder cet échange pour contribuer à l'amélioration des modèles.</span>
                </label>
                <p class="fon-data-note">
                  Audio et textes conservés uniquement sur cet ordinateur, jamais envoyés à OpenRouter.
                  L'audio de réponse sera régénéré après correction ; il est synthétique et ne sert pas de voix humaine cible pour le TTS.
                </p>
                <button id="fon-save-contribution" type="button" disabled>
                  Enregistrer ma contribution
                </button>
                <p id="fon-contribution-status" role="status" aria-live="polite"></p>
              </div>
              <div class="fon-transcript-footer"><span></span>Tu gardes le contrôle de tes corrections</div>
            </section>
          </main>
        </div>
        </div>
        <div id="fon-training-screen" class="fon-page fon-training-screen" hidden>
          <header class="fon-header">
            <div class="fon-brand">
              <span class="fon-brand-mark" aria-hidden="true">F</span>
              <div><strong>Contribuer au fon</strong><span>Une phrase à la fois</span></div>
            </div>
            <button class="fon-back-button" data-go-home type="button">← Accueil</button>
          </header>
          <main class="fon-training-layout">
            <section class="fon-training-card">
              <span class="fon-eyebrow">Collecte de phrases</span>
              <h1>Partage une traduction et sa prononciation</h1>
              <p class="fon-training-intro">Écris une phrase en français, sa traduction en fon, écoute la voix de l'IA puis enregistre une voix humaine si tu le souhaites.</p>
              <label class="fon-field">
                <span>Phrase en français</span>
                <textarea id="training-french" rows="2" maxlength="500"
                  placeholder="Exemple : Bonjour, comment vas-tu ?"></textarea>
              </label>
              <label class="fon-field">
                <span>Traduction en fon</span>
                <textarea id="training-fon" rows="3" maxlength="500"
                  placeholder="Écris ici la traduction en fon."></textarea>
              </label>
              <div class="fon-training-actions">
                <button id="training-play" class="fon-secondary-button" type="button">▶ Écouter la voix de l'IA</button>
                <button id="training-record" class="fon-secondary-button" type="button">● Enregistrer ma voix</button>
              </div>
              <audio id="training-audio" controls preload="none" hidden></audio>
              <p id="training-record-status" class="fon-training-status" role="status" aria-live="polite">
                L'enregistrement de ta voix est facultatif. Clique à nouveau pour terminer.
              </p>
              <label class="fon-consent fon-training-consent">
                <input id="training-consent" type="checkbox">
                <span>J'accepte de sauvegarder ces textes et l'enregistrement de ma voix (s'il existe) pour contribuer à l'amélioration des modèles.</span>
              </label>
              <p class="fon-data-note">Les données restent sur cet ordinateur. La voix de l'IA est conservée pour comparaison, mais seule ta lecture humaine peut servir de référence vocale pour entraîner le TTS. Tu peux enregistrer la paire de textes sans ajouter d'audio humain.</p>
              <button id="training-save" class="fon-save-button" type="button" disabled>Enregistrer cette contribution</button>
              <p id="training-save-status" class="fon-training-status" role="status" aria-live="polite"></p>
            </section>
          </main>
        </div>
        <style>
          :root { color-scheme: dark; }
          body {
            background: radial-gradient(ellipse at 18% 72%, rgba(52, 73, 190, .5), transparent 38%),
              radial-gradient(ellipse at 86% 20%, rgba(106, 34, 96, .22), transparent 34%),
              #101435 !important;
          }
          .gradio-container {
            width:100% !important; max-width:none !important; min-height:100vh;
            padding:0 34px 32px !important;
            background:radial-gradient(ellipse at 18% 72%,rgba(52,73,190,.5),transparent 38%),
              radial-gradient(ellipse at 86% 20%,rgba(106,34,96,.22),transparent 34%),#101435 !important;
          }
          footer { display: none !important; }
          #fon-voice-interface { width: 100%; }
          [hidden] { display:none !important; }
          #fon-voice-interface #fon-landing {
            min-height:calc(100vh - 32px); display:flex; flex-direction:column;
            color:#f8f6ff !important; font-family:Inter,ui-sans-serif,system-ui,sans-serif;
            background:radial-gradient(ellipse at 12% 75%,rgba(52,73,190,.32),transparent 38%),
              radial-gradient(ellipse at 88% 8%,rgba(106,34,96,.18),transparent 34%),#101435 !important;
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
            overflow:hidden; border:1px solid rgba(255,255,255,.12); border-radius:30px;
            background:radial-gradient(ellipse at 82% 18%,rgba(246,191,50,.12),transparent 40%),
              linear-gradient(135deg,rgba(39,47,94,.96),rgba(22,27,62,.94));
            box-shadow:0 24px 70px rgba(0,0,0,.2);
          }
          #fon-voice-interface .fon-landing-copy { text-align:left; }
          #fon-voice-interface .fon-eyebrow { color:#ffd348 !important; font-size:11px; font-weight:800; letter-spacing:.16em; text-transform:uppercase; }
          #fon-voice-interface .fon-landing-copy h1 { max-width:9ch; margin:15px 0 14px; color:#fff !important; font-size:clamp(38px,5.4vw,64px); line-height:.99; letter-spacing:-.045em; }
          #fon-voice-interface .fon-landing-copy p { max-width:430px; margin:0; color:#c3cae5 !important; font-size:16px; line-height:1.7; }
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
            border:1px solid rgba(255,255,255,.13) !important; border-radius:20px;
            background:linear-gradient(150deg,rgba(42,48,88,.95),rgba(28,32,68,.95)) !important;
            color:#f8f6ff !important; text-align:left; font:inherit; cursor:pointer;
            transition:transform .18s ease,border-color .18s ease,box-shadow .18s ease;
            text-decoration:none !important; box-shadow:0 12px 28px rgba(0,0,0,.12);
          }
          #fon-voice-interface .fon-mode-card:hover { transform:translateY(-4px); border-color:rgba(246,191,50,.65) !important; background:linear-gradient(150deg,#303964,#22294f) !important; box-shadow:0 18px 34px rgba(0,0,0,.22); }
          #fon-voice-interface .fon-mode-card:focus-visible { outline:3px solid #ffd348; outline-offset:3px; }
          #fon-voice-interface .fon-game-card { border-color:rgba(246,191,50,.42) !important; background:linear-gradient(150deg,rgba(84,62,81,.98),rgba(36,43,78,.98)) !important; }
          #fon-voice-interface .fon-card-topline { display:flex; align-items:center; justify-content:space-between; width:100%; margin-bottom:21px; }
          #fon-voice-interface .fon-mode-icon { display:grid; place-items:center; width:43px; height:43px; border-radius:14px; background:rgba(246,191,50,.16); color:#ffd348 !important; font-size:23px; font-weight:800; }
          #fon-voice-interface .fon-mode-icon-training { font-size:17px; }
          #fon-voice-interface .fon-card-tag { color:#d5d9ec !important; font-size:10px; font-weight:750; letter-spacing:.08em; text-transform:uppercase; }
          #fon-voice-interface .fon-mode-card strong { color:#fff !important; font-size:17px; line-height:1.3; }
          #fon-voice-interface .fon-mode-card > span:not(.fon-card-topline) { margin-top:8px; color:#bdc4e0 !important; font-size:13px; line-height:1.55; }
          #fon-voice-interface .fon-mode-card .fon-mode-action { display:flex; align-items:center; justify-content:space-between; gap:8px; width:100%; margin-top:auto !important; padding-top:22px; color:#ffd348 !important; font-size:13px; font-weight:750; }
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
          .fon-back-button,.fon-secondary-button,.fon-save-button {
            border:1px solid rgba(255,255,255,.17); border-radius:999px; padding:11px 16px;
            background:rgba(255,255,255,.06); color:#fff; font:inherit; cursor:pointer;
          }
          .fon-back-button:hover,.fon-secondary-button:hover:not(:disabled) { background:rgba(255,255,255,.13); }
          .fon-training-layout { display:grid; place-items:center; min-height:calc(100vh - 110px); padding:30px 0; }
          .fon-training-card { width:min(720px,100%); padding:clamp(22px,4vw,42px); border:1px solid rgba(255,255,255,.1); border-radius:24px; background:rgba(255,255,255,.055); box-shadow:0 24px 70px rgba(0,0,0,.2); }
          .fon-training-card h1 { font-size:clamp(26px,3vw,34px); }
          .fon-training-intro { margin-bottom:26px; }
          .fon-training-card .fon-field { margin-top:18px; }
          .fon-training-actions { display:flex; flex-wrap:wrap; gap:10px; margin-top:18px; }
          .fon-secondary-button { border-color:rgba(246,191,50,.38); color:#ffda6f; }
          .fon-secondary-button:disabled,.fon-save-button:disabled { opacity:.5; cursor:not-allowed; }
          #training-audio { width:100%; margin-top:16px; }
          .fon-training-status { min-height:22px; color:#b9c0df; font-size:13px; }
          .fon-training-status[data-state="error"] { color:#ff9099; }
          .fon-training-status[data-state="success"] { color:#70e1a8; }
          .fon-training-consent { margin-top:20px; }
          .fon-save-button { width:100%; margin-top:12px; border:0; background:linear-gradient(135deg,#ffd348,#f3aa25); color:#182044; font-weight:800; }
          .fon-save-button:hover:not(:disabled) { filter:brightness(1.06); }
          .fon-page { min-height: 100vh; color: #fff; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
          .fon-header {
            display: flex; justify-content: space-between; align-items: center;
            min-height: 92px; border-bottom: 1px solid rgba(255,255,255,.09);
          }
          .fon-brand { display: flex; align-items: center; gap: 12px; }
          .fon-brand-mark {
            display: grid; place-items: center; width: 42px; height: 42px; border-radius: 14px;
            background: linear-gradient(145deg,#f6bd26,#eb8f32); color: #15193e;
            font-size: 22px; font-weight: 900;
          }
          .fon-brand strong,.fon-brand span { display:block; }
          .fon-brand strong { font-size: 17px; letter-spacing: .01em; }
          .fon-brand div span { margin-top: 3px; color: #aeb5d7; font-size: 13px; }
          .fon-language { display:flex; align-items:center; gap:10px; color:#bfc5e1; font-size:13px; }
          .fon-language select {
            min-width: 128px; padding: 10px 34px 10px 14px; border: 1px solid rgba(255,255,255,.2);
            border-radius: 999px; background:#1b2048; color:#fff; font:inherit; cursor:pointer;
          }
          .fon-layout {
            display:grid; grid-template-columns:minmax(0, .92fr) minmax(0, 1.08fr);
            gap: clamp(24px, 6vw, 88px); align-items:center; max-width:1120px;
            min-height: min(690px, calc(100vh - 94px)); margin:0 auto; padding:30px 0;
          }
          .fon-hero { display:flex; flex-direction:column; align-items:center; text-align:center; }
          .fon-guide-halo {
            display:grid; place-items:center; width:100%; min-height:460px;
            background:radial-gradient(ellipse,rgba(244,178,42,.13),rgba(70,86,190,.05) 48%,transparent 72%);
          }
          #fon-guide { width:auto; height:min(58vh,500px); max-width:100%; }
          #fon-guide svg { display:block; width:auto; height:100%; overflow:visible; filter:drop-shadow(0 18px 26px rgba(0,0,0,.24)); }
          .fon-guide-arm { transform-box:view-box; transform-origin:166px 246px; }
          #fon-guide[data-state="idle"] .fon-guide-arm,
          #fon-guide[data-state="listening"] .fon-guide-arm { animation:fon-guide-wave 2.4s ease-in-out infinite; }
          #fon-guide[data-state="speaking"] .fon-guide-mouth {
            transform-box:fill-box; transform-origin:center; animation:fon-guide-talk .24s ease-in-out infinite alternate;
          }
          @keyframes fon-guide-wave { 0%,100% { transform:rotate(0); } 50% { transform:rotate(7deg); } }
          @keyframes fon-guide-talk { from { transform:scaleY(.65); } to { transform:scaleY(1.2); } }
          #fon-mic-start {
            display:flex; align-items:center; justify-content:center; gap:12px; min-width:230px;
            min-height:62px; margin-top:-4px; padding:14px 28px; border:0; border-radius:999px;
            background:linear-gradient(135deg,#ffd348,#f3aa25); color:#182044;
            box-shadow:0 12px 32px rgba(245,177,38,.26); font-size:18px; font-weight:750;
            cursor:pointer; transition:transform .18s ease, box-shadow .18s ease, background .18s ease;
          }
          #fon-mic-start:hover:not(:disabled) { transform:translateY(-2px); box-shadow:0 16px 38px rgba(245,177,38,.34); }
          #fon-mic-start svg { width:23px; height:23px; }
          #fon-mic-start[data-state="listening"] { background:linear-gradient(135deg,#ef6675,#d84161); color:#fff; box-shadow:0 12px 32px rgba(216,65,97,.27); }
          #fon-mic-start[data-state="processing"],#fon-mic-start:disabled { opacity:.76; cursor:wait; }
          #fon-mic-status { min-height:24px; margin:14px 0 0; color:#b9c0df; font-size:14px; }
          #fon-mic-status[data-state="error"] { color:#ff9099; font-weight:650; }
          #fon-progress-track {
            width:min(280px,90%); height:7px; margin-top:14px; overflow:hidden; border-radius:999px;
            background:rgba(255,255,255,.16);
          }
          #fon-progress-track[data-mode="hidden"] { display:none; }
          #fon-progress-fill { height:100%; width:0; border-radius:inherit; background:#f6bf32; transition:width 100ms linear; }
          #fon-progress-track[data-mode="indeterminate"] #fon-progress-fill { width:35% !important; animation:fon-progress-slide 1.1s ease-in-out infinite alternate; }
          #fon-progress-track[data-mode="complete"] #fon-progress-fill { background:#35bb83; }
          #fon-progress-track[data-mode="error"] #fon-progress-fill { width:100%; background:#ef6675; }
          #fon-replay {
            margin-top:10px; padding:10px 18px; border:1px solid rgba(255,255,255,.24);
            border-radius:999px; background:rgba(255,255,255,.08); color:#fff;
            font-size:14px; font-weight:650; cursor:pointer;
          }
          .fon-transcript-panel {
            display:flex; flex-direction:column; min-height:440px; padding:clamp(26px,4vw,48px);
            border-radius:26px; background:#fff; color:#202344;
            box-shadow:0 24px 70px rgba(0,0,0,.24);
          }
          .fon-transcript-heading { display:flex; align-items:center; gap:16px; padding-bottom:24px; border-bottom:1px solid #ececf3; }
          .fon-transcript-icon {
            display:grid; place-items:center; width:48px; height:48px; border-radius:15px;
            background:#fff3ce; color:#ad7410 !important; font-size:18px; font-weight:800;
          }
          .fon-transcript-heading h1 { margin:0; color:#202344 !important; font-size:clamp(22px,3vw,30px); line-height:1.15; font-weight:780; }
          .fon-transcript-heading p { margin:6px 0 0; color:#81849a !important; font-size:14px; }
          .fon-field { display:flex; flex-direction:column; gap:9px; margin-top:22px; color:#4b4d68 !important; font-size:14px; font-weight:700; }
          .fon-field span { color:#4b4d68 !important; }
          .fon-field textarea {
            width:100%; box-sizing:border-box; resize:vertical; min-height:92px; padding:14px 15px;
            border:1px solid #dedfeb; border-radius:13px; background:#fbfbfd; color:#30324c;
            font-family:inherit; font-size:16px; font-weight:500; line-height:1.6; outline:none;
          }
          .fon-field textarea:focus { border-color:#6874d8; box-shadow:0 0 0 3px rgba(104,116,216,.14); }
          .fon-field textarea::placeholder { color:#a0a2b3; font-weight:400; }
          #fon-answer { min-height:118px; }
          #fon-response-audio { width:100%; margin-top:18px; }
          #fon-contribution { margin-top:20px; padding:16px; border-radius:15px; background:#f4f5fb; }
          #fon-contribution[hidden] { display:none; }
          .fon-consent { display:flex; align-items:flex-start; gap:10px; color:#3e405c !important; font-size:14px; line-height:1.5; cursor:pointer; }
          .fon-consent span { color:#3e405c !important; }
          .fon-consent input { flex:0 0 auto; width:18px; height:18px; margin:1px 0 0; accent-color:#4856c8; }
          .fon-data-note { margin:10px 0 14px; color:#777a92 !important; font-size:12px; line-height:1.5; }
          #fon-save-contribution {
            width:100%; padding:12px 16px; border:0; border-radius:11px;
            background:#4856c8; color:#fff; font-size:14px; font-weight:700; cursor:pointer;
          }
          #fon-save-contribution:disabled { opacity:.48; cursor:not-allowed; }
          #fon-contribution-status { margin:10px 0 0; color:#62657d !important; font-size:13px; line-height:1.5; }
          #fon-contribution-status[data-state="error"] { color:#c5354d; }
          #fon-contribution-status[data-state="success"] { color:#16875b; }
          #fon-transcript {
            min-height:92px; color:#383b57; font-size:16px; line-height:1.6;
          }
          .fon-transcript-footer {
            display:flex; align-items:center; gap:9px; color:#9194a8 !important; font-size:12px;
          }
          .fon-transcript-footer span { width:8px; height:8px; border-radius:50%; background:#35bb83; }
          @keyframes fon-progress-slide { from { margin-left:0; } to { margin-left:65%; } }
          @media (prefers-reduced-motion:reduce) {
            #fon-guide *,#fon-progress-fill,#fon-mic-start { animation:none !important; transition:none !important; }
          }
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
        </style>
        """,
        elem_id="fon-voice-interface",
    )

    demo.load(fn=None, inputs=None, outputs=None, js=MICROPHONE_JS)


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
        )
    except Exception as error:
        LOGGER.exception("Could not save a consented Fon training example")
        raise HTTPException(
            status_code=500,
            detail="Impossible d'enregistrer la contribution sur cet ordinateur.",
        ) from error

    return {"sample_id": sample_id, "assistant_audio": assistant_audio}


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
    contribution_source = payload.get("source", "training")
    if contribution_source not in ("training", "game"):
        raise HTTPException(status_code=400, detail="La source de contribution est invalide.")
    mission_id = payload.get("mission_id")
    mission_title = payload.get("mission_title")
    if contribution_source == "game":
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

    human_audio = decode_training_phrase_audio(payload.get("human_audio"), "L'audio humain")
    if contribution_source == "game" and human_audio is None:
        raise HTTPException(
            status_code=400,
            detail="Un enregistrement vocal est requis pour cette contribution au jeu.",
        )
    synthesized_audio = decode_training_phrase_audio(
        payload.get("synthesized_audio"),
        "L'audio synthétisé",
    )
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
            contribution_source != "game",
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

web_app = gr.mount_gradio_app(web_app, demo, path="/")


if __name__ == "__main__":
    uvicorn.run(
        web_app,
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "7861")),
    )
