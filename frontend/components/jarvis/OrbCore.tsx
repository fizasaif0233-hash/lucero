"use client";

import Image from "next/image";
import { cn } from "@/lib/utils";
import type { VoiceMode, VoicePhase } from "@/hooks/useVoice";

interface OrbCoreProps {
  mode: VoiceMode;
  phase?: VoicePhase;
  onOrbClick?: () => void;
}

export function OrbCore({ mode, phase, onOrbClick }: OrbCoreProps) {
  const resolved: VoicePhase =
    phase ||
    (mode === "speaking"
      ? "speaking"
      : mode === "processing"
        ? "thinking"
        : mode === "listening_wake" || mode === "listening_command"
          ? "listening"
          : mode === "unsupported"
            ? "unsupported"
            : "off");

  const active =
    resolved === "listening" ||
    resolved === "thinking" ||
    resolved === "speaking";

  const statusText =
    resolved === "speaking"
      ? "Speaking"
      : resolved === "thinking"
        ? "Thinking"
        : resolved === "listening"
          ? "Listening"
          : resolved === "unsupported"
            ? "Voice unsupported"
            : "Ready";

  return (
    <div className="relative flex w-full max-w-full flex-col items-center justify-center py-1">
      <button
        type="button"
        onClick={onOrbClick}
        className="relative aspect-square w-[min(42vh,240px)] sm:w-[min(46vh,280px)] rounded-full focus:outline-none"
        title={resolved === "speaking" ? "Stop speaking" : "Talk"}
      >
        <div
          className={cn(
            "absolute inset-0 rounded-full orb-ring animate-spinSlow opacity-50",
            active && "shadow-glow-lg"
          )}
        />
        <div className="absolute inset-[6%] rounded-full overflow-hidden">
          <Image
            src="/brand/lucero.webp"
            alt="L.U.C.E.R.O"
            fill
            priority
            sizes="(max-width: 640px) 240px, 280px"
            className={cn(
              "object-cover scale-110 transition duration-500",
              active && "animate-orbPulse"
            )}
          />
        </div>
        {active && (
          <div className="pointer-events-none absolute inset-0 rounded-full ring-2 ring-jarvis-cyan/40 shadow-glow" />
        )}
      </button>

      <h1 className="mt-3 font-display text-3xl sm:text-4xl tracking-[0.2em] text-jarvis-text">
        L.U.C.E.R.O
      </h1>
      <p className="mt-2 flex items-center gap-2 text-sm text-jarvis-muted">
        <span
          className={cn(
            "h-2 w-2 rounded-full",
            resolved === "off" || resolved === "unsupported"
              ? "bg-jarvis-muted"
              : resolved === "speaking" || resolved === "thinking"
                ? "bg-jarvis-warn"
                : "bg-jarvis-success"
          )}
        />
        {statusText}
      </p>
    </div>
  );
}
