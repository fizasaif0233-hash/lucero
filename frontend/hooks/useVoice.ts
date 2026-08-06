"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/** Stable UI phases — no rapid wake/command flicker */
export type VoicePhase = "off" | "listening" | "thinking" | "speaking" | "unsupported";

/** @deprecated keep for OrbCore compatibility */
export type VoiceMode =
  | "unsupported"
  | "idle"
  | "listening_wake"
  | "listening_command"
  | "speaking"
  | "processing";

type SpeechRecognitionLike = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  maxAlternatives?: number;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  onstart: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
};

type SpeechRecognitionEventLike = {
  resultIndex: number;
  results: ArrayLike<{
    isFinal: boolean;
    length: number;
    0: { transcript: string };
  }>;
};

function getRecognitionCtor(): (new () => SpeechRecognitionLike) | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as {
    SpeechRecognition?: new () => SpeechRecognitionLike;
    webkitSpeechRecognition?: new () => SpeechRecognitionLike;
  };
  return w.SpeechRecognition || w.webkitSpeechRecognition || null;
}

function stripMarkdown(text: string): string {
  return text
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/[*_#>\-\[\]\(\)]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function extractAfterWake(transcript: string): string {
  const lower = transcript.toLowerCase();
  const patterns = [
    /\bhey\s+lucero\b[,.]?\s*/i,
    /\bok(?:ay)?\s+lucero\b[,.]?\s*/i,
    /\bl\.?\s*u\.?\s*c\.?\s*e\.?\s*r\.?\s*o\b[,.]?\s*/i,
    /\blucero\b[,.]?\s*/i,
    /\bhey\s+jarvis\b[,.]?\s*/i,
    /\bjarvis\b[,.]?\s*/i,
  ];
  for (const pattern of patterns) {
    const match = lower.match(pattern);
    if (match && match.index !== undefined) {
      return transcript.slice(match.index + match[0].length).trim() || transcript;
    }
  }
  return transcript.trim();
}

async function ensureMicPermission(): Promise<boolean> {
  if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
    return true;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    stream.getTracks().forEach((t) => t.stop());
    return true;
  } catch {
    return false;
  }
}

function phaseToMode(phase: VoicePhase): VoiceMode {
  switch (phase) {
    case "listening":
      return "listening_wake";
    case "thinking":
      return "processing";
    case "speaking":
      return "speaking";
    case "unsupported":
      return "unsupported";
    default:
      return "idle";
  }
}

interface UseVoiceOptions {
  enabled?: boolean;
  onCommand: (text: string) => Promise<string | void> | string | void;
}

export function useVoice({ enabled = true, onCommand }: UseVoiceOptions) {
  const [phase, setPhase] = useState<VoicePhase>("off");
  const [supported, setSupported] = useState(true);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [micOn, setMicOn] = useState(false);
  const [speakerOn, setSpeakerOn] = useState(true);

  const recRef = useRef<SpeechRecognitionLike | null>(null);
  const phaseRef = useRef<VoicePhase>("off");
  const micOnRef = useRef(false);
  const speakerOnRef = useRef(true);
  const busyRef = useRef(false); // thinking or speaking
  const onCommandRef = useRef(onCommand);
  const keepListeningRef = useRef(false);
  const speakResolveRef = useRef<(() => void) | null>(null);
  const bufferRef = useRef("");
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const restartTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    onCommandRef.current = onCommand;
  }, [onCommand]);

  useEffect(() => {
    micOnRef.current = micOn;
  }, [micOn]);

  useEffect(() => {
    speakerOnRef.current = speakerOn;
  }, [speakerOn]);

  useEffect(() => {
    if (!enabled) return;
    if (!getRecognitionCtor()) {
      setSupported(false);
      setPhase("unsupported");
      phaseRef.current = "unsupported";
    }
  }, [enabled]);

  const setStablePhase = useCallback((next: VoicePhase) => {
    if (phaseRef.current === next) return;
    phaseRef.current = next;
    setPhase(next);
  }, []);

  const clearSilence = useCallback(() => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
  }, []);

  const stopSpeaking = useCallback(() => {
    if (typeof window !== "undefined") window.speechSynthesis.cancel();
    if (speakResolveRef.current) {
      speakResolveRef.current();
      speakResolveRef.current = null;
    }
  }, []);

  const scheduleListenRestart = useCallback(() => {
    if (restartTimerRef.current) clearTimeout(restartTimerRef.current);
    restartTimerRef.current = setTimeout(() => {
      if (
        !keepListeningRef.current ||
        !micOnRef.current ||
        busyRef.current ||
        phaseRef.current === "unsupported"
      ) {
        return;
      }
      try {
        recRef.current?.start();
      } catch {
        /* already running */
      }
      setStablePhase("listening");
    }, 350);
  }, [setStablePhase]);

  const speak = useCallback(
    async (text: string) => {
      if (!speakerOnRef.current || typeof window === "undefined") {
        busyRef.current = false;
        if (micOnRef.current) {
          keepListeningRef.current = true;
          setStablePhase("listening");
          scheduleListenRestart();
        } else {
          setStablePhase("off");
        }
        return;
      }

      const clean = stripMarkdown(text);
      if (!clean) {
        busyRef.current = false;
        if (micOnRef.current) {
          keepListeningRef.current = true;
          setStablePhase("listening");
          scheduleListenRestart();
        } else setStablePhase("off");
        return;
      }

      keepListeningRef.current = false;
      clearSilence();
      try {
        recRef.current?.stop();
      } catch {
        /* ignore */
      }

      window.speechSynthesis.cancel();
      window.speechSynthesis.resume();
      busyRef.current = true;
      setError(null);
      setTranscript("");
      setStablePhase("speaking");

      await new Promise<void>((resolve) => {
        speakResolveRef.current = resolve;
        const utterance = new SpeechSynthesisUtterance(clean);
        utterance.rate = 1.02;
        utterance.pitch = 0.95;
        const voices = window.speechSynthesis.getVoices();
        const preferred = voices.find((v) => /^en/i.test(v.lang)) || voices[0];
        if (preferred) utterance.voice = preferred;
        utterance.onend = () => {
          speakResolveRef.current = null;
          resolve();
        };
        utterance.onerror = () => {
          speakResolveRef.current = null;
          resolve();
        };
        window.speechSynthesis.speak(utterance);
      });

      busyRef.current = false;
      if (micOnRef.current) {
        keepListeningRef.current = true;
        setStablePhase("listening");
        scheduleListenRestart();
      } else {
        setStablePhase("off");
      }
    },
    [clearSilence, scheduleListenRestart, setStablePhase]
  );

  const runCommand = useCallback(
    async (command: string) => {
      const text = extractAfterWake(command);
      if (!text || text.length < 2 || busyRef.current) return;

      busyRef.current = true;
      clearSilence();
      bufferRef.current = "";
      setTranscript(text);
      setError(null);
      setStablePhase("thinking");
      keepListeningRef.current = false;

      try {
        recRef.current?.stop();
      } catch {
        /* ignore */
      }

      try {
        const reply = await onCommandRef.current(text);
        if (typeof reply === "string" && reply.trim()) {
          await speak(reply);
        } else {
          busyRef.current = false;
          if (micOnRef.current) {
            keepListeningRef.current = true;
            setStablePhase("listening");
            scheduleListenRestart();
          } else {
            setStablePhase("off");
          }
        }
      } catch (err) {
        busyRef.current = false;
        setError((err as Error).message || "Request failed");
        if (micOnRef.current) {
          keepListeningRef.current = true;
          setStablePhase("listening");
          scheduleListenRestart();
        } else {
          setStablePhase("off");
        }
      } finally {
        setTranscript("");
      }
    },
    [clearSilence, scheduleListenRestart, setStablePhase, speak]
  );

  const attachRecognition = useCallback(() => {
    const Ctor = getRecognitionCtor();
    if (!Ctor) return null;

    try {
      recRef.current?.abort();
    } catch {
      /* ignore */
    }

    const recognition = new Ctor();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onstart = () => {
      // stay on listening — don't flicker other phases
      if (!busyRef.current && micOnRef.current) {
        setStablePhase("listening");
      }
    };

    recognition.onresult = (event) => {
      if (busyRef.current) return;

      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const piece = event.results[i][0].transcript.trim();
        if (!piece) continue;
        if (event.results[i].isFinal) {
          bufferRef.current = `${bufferRef.current} ${piece}`.trim();
          setTranscript(bufferRef.current);
          clearSilence();
          silenceTimerRef.current = setTimeout(() => {
            const raw = bufferRef.current.trim();
            bufferRef.current = "";
            if (raw.length >= 2) void runCommand(raw);
          }, 1000);
        } else {
          interim += piece;
        }
      }
      if (interim && !busyRef.current) {
        setTranscript(
          bufferRef.current ? `${bufferRef.current} ${interim}`.trim() : interim
        );
      }
    };

    recognition.onerror = (event) => {
      // Ignore transient recognition noise — prevents UI flicker
      if (
        event.error === "no-speech" ||
        event.error === "aborted" ||
        event.error === "network"
      ) {
        return;
      }
      if (event.error === "not-allowed") {
        setError("Microphone blocked. Allow mic for this site.");
        setMicOn(false);
        micOnRef.current = false;
        keepListeningRef.current = false;
        setStablePhase("off");
      }
    };

    recognition.onend = () => {
      if (keepListeningRef.current && micOnRef.current && !busyRef.current) {
        scheduleListenRestart();
      }
    };

    recRef.current = recognition;
    return recognition;
  }, [clearSilence, runCommand, scheduleListenRestart, setStablePhase]);

  const enableMic = useCallback(async () => {
    if (!getRecognitionCtor()) {
      setSupported(false);
      setStablePhase("unsupported");
      return;
    }
    const ok = await ensureMicPermission();
    if (!ok) {
      setError("Microphone blocked. Allow mic for localhost:3000.");
      return;
    }
    setError(null);
    setMicOn(true);
    micOnRef.current = true;
    keepListeningRef.current = true;
    busyRef.current = false;
    setStablePhase("listening");
    const rec = attachRecognition();
    try {
      rec?.start();
    } catch {
      /* ignore */
    }
  }, [attachRecognition, setStablePhase]);

  const disableMic = useCallback(() => {
    setMicOn(false);
    micOnRef.current = false;
    keepListeningRef.current = false;
    clearSilence();
    bufferRef.current = "";
    stopSpeaking();
    busyRef.current = false;
    try {
      recRef.current?.abort();
    } catch {
      /* ignore */
    }
    recRef.current = null;
    setTranscript("");
    setError(null);
    setStablePhase("off");
  }, [clearSilence, setStablePhase, stopSpeaking]);

  const toggleMic = useCallback(() => {
    if (micOnRef.current) disableMic();
    else void enableMic();
  }, [disableMic, enableMic]);

  const toggleSpeaker = useCallback(() => {
    setSpeakerOn((v) => {
      if (v) stopSpeaking();
      return !v;
    });
  }, [stopSpeaking]);

  const interrupt = useCallback(() => {
    stopSpeaking();
    speakResolveRef.current = null;
    busyRef.current = false;
    bufferRef.current = "";
    setTranscript("");
    setError(null);
    if (micOnRef.current) {
      keepListeningRef.current = true;
      setStablePhase("listening");
      scheduleListenRestart();
    } else {
      // Start listening after interrupt even if mic was conceptually on via talk
      void enableMic();
    }
  }, [enableMic, scheduleListenRestart, setStablePhase, stopSpeaking]);

  const pushToTalk = useCallback(() => {
    stopSpeaking();
    busyRef.current = false;
    setError(null);
    if (!micOnRef.current) {
      void enableMic();
    } else {
      keepListeningRef.current = true;
      setStablePhase("listening");
      scheduleListenRestart();
    }
  }, [enableMic, scheduleListenRestart, setStablePhase, stopSpeaking]);

  useEffect(() => {
    return () => {
      keepListeningRef.current = false;
      clearSilence();
      if (restartTimerRef.current) clearTimeout(restartTimerRef.current);
      stopSpeaking();
      try {
        recRef.current?.abort();
      } catch {
        /* ignore */
      }
    };
  }, [clearSilence, stopSpeaking]);

  const mode = phaseToMode(phase);

  return {
    phase,
    mode,
    supported,
    transcript,
    error,
    micOn,
    speakerOn,
    listeningLive: phase === "listening",
    toggleMic,
    toggleSpeaker,
    pushToTalk,
    interrupt,
    speak,
    stopSpeaking,
  };
}
