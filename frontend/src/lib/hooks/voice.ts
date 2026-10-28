"use client";

import * as React from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import { normalizeVoiceState, str } from "@/lib/api/normalize";
import { translate, useLocale } from "@/lib/i18n/locale-context";
import type { VoiceState } from "@/lib/api/types";
import { fail } from "./failure";

/**
 * The interview's voice seam (19.6), browser side.
 *
 * Voice is an enhancement, never a precondition: every capability here is
 * probed, and a deployment without a speech provider, a browser without a
 * recorder, or a denied microphone all fall back to the text box the runner
 * has always had. The page never renders a control it cannot honour.
 *
 * The server half transcribes and speaks through the deployment's provider;
 * when there is none, the browser's own speech APIs (SpeechRecognition and
 * speechSynthesis) take over, which is why those are probed separately from
 * the server's `stt`/`tts` flags.
 */

export const NO_VOICE: VoiceState = { provider: "", stt: false, tts: false };

export type VoiceInputMode = "service" | "browser" | "typing";
export type VoiceOutputMode = "service" | "browser" | "none";

/** How an answer gets in: the server's ears, the browser's, or the keyboard. */
export function pickVoiceInputMode(serviceStt: boolean, browserStt: boolean): VoiceInputMode {
  if (serviceStt) return "service";
  if (browserStt) return "browser";
  return "typing";
}

/** How a question gets out: the server's voice, the browser's, or silence. */
export function pickVoiceOutputMode(serviceTts: boolean, browserTts: boolean): VoiceOutputMode {
  if (serviceTts) return "service";
  if (browserTts) return "browser";
  return "none";
}

/**
 * The recorded clip as bare base64. Deliberately not a FileReader: its only
 * output is its own `.result`, and the stream census treats any `.result`
 * read in the browser as a claim about the terminal frame.
 */
export async function clipBase64(blob: Blob): Promise<string> {
  const bytes = new Uint8Array(await blob.arrayBuffer());
  let binary = "";
  for (let i = 0; i < bytes.length; i += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  }
  return btoa(binary);
}

export function audioDataUrl(mime: string, base64: string): string {
  return `data:${mime || "audio/wav"};base64,${base64}`;
}

export function speechLang(locale: string): string {
  return locale === "zh" ? "zh-CN" : "en-US";
}

/**
 * The deployment's capabilities, read once. A failure is "no provider" --
 * the page then offers the browser's speech and the text box, which is what
 * a reader whose ai-service is down needs anyway.
 */
export function useVoiceState() {
  return useQuery({
    queryKey: ["interview", "voice"],
    queryFn: async (): Promise<VoiceState> => {
      try {
        return normalizeVoiceState(await api.get<unknown>(endpoints.interviewVoice));
      } catch {
        return NO_VOICE;
      }
    },
    staleTime: 5 * 60_000,
    retry: false,
  });
}

export type VoiceTranscript = { text: string; provider: string };

export function useTranscribeAnswer(sessionId: string) {
  const { locale } = useLocale();
  return useMutation({
    mutationFn: async (clip: { audio: string; mime?: string }): Promise<VoiceTranscript> => {
      const raw = await api.request<unknown>(endpoints.interviewVoiceTranscribe(sessionId), {
        method: "POST",
        body: { audio: clip.audio, mime: clip.mime || "audio/webm", locale },
      });
      return { text: str(raw, "text") ?? "", provider: str(raw, "provider") ?? "" };
    },
    onError: fail("Couldn't transcribe that recording."),
  });
}

export function useSpeakQuestion(sessionId: string) {
  const { locale } = useLocale();
  return useMutation({
    mutationFn: async (text: string): Promise<{ audio: string; mime: string }> => {
      const raw = await api.request<unknown>(endpoints.interviewVoiceSpeak(sessionId), {
        method: "POST",
        body: { text, locale },
      });
      return { audio: str(raw, "audio") ?? "", mime: str(raw, "mime") ?? "audio/wav" };
    },
    onError: fail("Couldn't speak that question."),
  });
}

/* --------------------------- the browser's own speech --------------------------- */

interface SpeechRecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start(): void;
  stop(): void;
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
}

function speechRecognitionCtor(): (new () => SpeechRecognitionLike) | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as Record<string, unknown>;
  const ctor = w.SpeechRecognition ?? w.webkitSpeechRecognition;
  return typeof ctor === "function" ? (ctor as new () => SpeechRecognitionLike) : null;
}

const RECORDER_MIMES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/mp4",
  "audio/ogg;codecs=opus",
];

function pickRecorderMime(): string {
  if (typeof MediaRecorder === "undefined" || typeof MediaRecorder.isTypeSupported !== "function") {
    return "";
  }
  return RECORDER_MIMES.find((m) => MediaRecorder.isTypeSupported(m)) ?? "";
}

/**
 * The one answer recorder: a mic button, a stop button and the transcript the
 * page puts in the answer box. The recorded clip never outlives the request --
 * it is transcribed, appended to the box, and dropped; nothing is stored.
 */
export function useAnswerVoice(sessionId: string, onTranscript: (text: string) => void) {
  const { locale } = useLocale();
  const voiceState = useVoiceState();
  const transcribe = useTranscribeAnswer(sessionId);
  const speaker = useSpeakQuestion(sessionId);

  const [status, setStatus] = React.useState<"idle" | "recording" | "transcribing">("idle");
  const [error, setError] = React.useState<string | null>(null);
  const [speaking, setSpeaking] = React.useState(false);

  const recorderRef = React.useRef<MediaRecorder | null>(null);
  const streamRef = React.useRef<MediaStream | null>(null);
  const recognitionRef = React.useRef<SpeechRecognitionLike | null>(null);
  const audioRef = React.useRef<HTMLAudioElement | null>(null);
  const capTimerRef = React.useRef<number | null>(null);
  const onTranscriptRef = React.useRef(onTranscript);
  React.useEffect(() => {
    onTranscriptRef.current = onTranscript;
  }, [onTranscript]);

  const [caps] = React.useState(() => ({
    recorder:
      typeof window !== "undefined" &&
      typeof window.MediaRecorder !== "undefined" &&
      typeof navigator.mediaDevices?.getUserMedia === "function",
    recognition: speechRecognitionCtor() !== null,
    synthesis: typeof window !== "undefined" && typeof window.speechSynthesis !== "undefined",
  }));

  const state = voiceState.data ?? NO_VOICE;
  const inputMode = pickVoiceInputMode(state.stt && caps.recorder, caps.recognition);
  const outputMode = pickVoiceOutputMode(state.tts, caps.synthesis);

  const stopStream = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  };

  const finishClip = async (blob: Blob, mime: string) => {
    setStatus("transcribing");
    try {
      const clip = await clipBase64(blob);
      transcribe.mutate(
        { audio: clip, mime },
        {
          onSuccess: (answer) => {
            const text = answer.text.trim();
            if (text) {
              onTranscriptRef.current(text);
            } else {
              setError(
                translate("interviews.detail.voiceFailed") ??
                  "Voice didn't come through — try again or type your answer."
              );
            }
          },
          onSettled: () => setStatus("idle"),
        }
      );
    } catch {
      setStatus("idle");
      setError(
        translate("interviews.detail.recordingFailed") ??
          "Couldn't read that recording — try again or type your answer."
      );
    }
  };

  const stop = () => {
    if (capTimerRef.current !== null) {
      window.clearTimeout(capTimerRef.current);
      capTimerRef.current = null;
    }
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      return;
    }
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.stop();
    }
  };

  const startRecording = async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const mime = pickRecorderMime();
      const recorder = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
      const chunks: Blob[] = [];
      recorder.ondataavailable = (event) => {
        chunks.push(event.data);
      };
      recorder.onstop = () => {
        stopStream();
        const type = recorder.mimeType || mime || "audio/webm";
        void finishClip(new Blob(chunks, { type }), type);
      };
      recorderRef.current = recorder;
      recorder.start();
      setStatus("recording");
      // Two minutes is an answer, not a recording session: the cap keeps one
      // tab from holding the microphone (and the speech budget) open.
      capTimerRef.current = window.setTimeout(stop, 120_000);
    } catch {
      stopStream();
      setError(
        translate("interviews.detail.micDenied") ??
          "The microphone wasn't available — you can still type your answer."
      );
    }
  };

  const startRecognition = () => {
    const Ctor = speechRecognitionCtor();
    if (!Ctor) {
      setError(
        translate("interviews.detail.voiceUnavailable") ??
          "Voice isn't available here — you can still type your answer."
      );
      return;
    }
    const recognition = new Ctor();
    recognition.lang = speechLang(locale);
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.onresult = (event) => {
      let said = "";
      for (let i = 0; i < event.results.length; i += 1) {
        said += event.results[i][0]?.transcript ?? "";
      }
      const text = said.trim();
      if (text) {
        onTranscriptRef.current(text);
      } else {
        setError(
          translate("interviews.detail.voiceFailed") ??
            "Voice didn't come through — try again or type your answer."
        );
      }
    };
    recognition.onerror = () =>
      setError(
        translate("interviews.detail.voiceFailed") ??
          "Voice didn't come through — try again or type your answer."
      );
    recognition.onend = () => {
      recognitionRef.current = null;
      setStatus("idle");
    };
    recognitionRef.current = recognition;
    setStatus("recording");
    recognition.start();
  };

  const start = () => {
    if (status !== "idle") return;
    setError(null);
    if (inputMode === "service") {
      void startRecording();
      return;
    }
    if (inputMode === "browser") {
      startRecognition();
      return;
    }
    setError(
      translate("interviews.detail.voiceUnavailable") ??
        "Voice isn't available here — you can still type your answer."
    );
  };

  const stopSpeaking = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (typeof window !== "undefined" && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    setSpeaking(false);
  };

  const speak = (text: string) => {
    const line = text.trim();
    if (!line) return;
    setError(null);
    if (outputMode === "service") {
      speaker.mutate(line, {
        onSuccess: ({ audio, mime }) => {
          if (!audio) return;
          stopSpeaking();
          const element = new Audio(audioDataUrl(mime, audio));
          audioRef.current = element;
          element.onended = () => setSpeaking(false);
          setSpeaking(true);
          void element.play().catch(() => {
            stopSpeaking();
            setError(
              translate("interviews.detail.speechUnavailable") ??
                "Couldn't play the question — read it above."
            );
          });
        },
      });
      return;
    }
    if (outputMode === "browser") {
      stopSpeaking();
      const utterance = new SpeechSynthesisUtterance(line);
      utterance.lang = speechLang(locale);
      utterance.onend = () => setSpeaking(false);
      setSpeaking(true);
      window.speechSynthesis.speak(utterance);
      return;
    }
    setError(
      translate("interviews.detail.speechUnavailable") ??
        "Couldn't play the question — read it above."
    );
  };

  React.useEffect(
    () => () => {
      if (capTimerRef.current !== null) window.clearTimeout(capTimerRef.current);
      streamRef.current?.getTracks().forEach((track) => track.stop());
      try {
        recognitionRef.current?.stop();
      } catch {
        /* already stopped */
      }
      audioRef.current?.pause();
      if (typeof window !== "undefined" && window.speechSynthesis) window.speechSynthesis.cancel();
    },
    []
  );

  return {
    inputMode,
    outputMode,
    canRecord: inputMode !== "typing",
    canSpeak: outputMode !== "none",
    status,
    recording: status === "recording",
    busy: status !== "idle",
    error,
    clearError: () => setError(null),
    start,
    stop,
    speak,
    stopSpeaking,
    speaking,
  };
}
