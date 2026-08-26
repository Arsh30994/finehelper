"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { Mic, Send, Volume2 } from "lucide-react";
import {
  agentChat,
  agentVoiceStt,
  agentVoiceTts,
  type AgentChatResult,
} from "@/api";
import { FadeUp, Skeleton } from "@/components/motion";
import { ErrorText, PageHeader, btnPrimaryClass } from "@/components/ui";
import { cn } from "@/lib/utils";

type Msg = {
  id: string;
  role: "user" | "agent";
  text: string;
  meta?: Pick<AgentChatResult, "intent" | "tools_used" | "score">;
  via?: "voice" | "text";
};

function pickMime(): string {
  if (typeof MediaRecorder === "undefined") return "audio/webm";
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg"];
  return candidates.find((t) => MediaRecorder.isTypeSupported(t)) || "audio/webm";
}

export default function AgentPage() {
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [listening, setListening] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [error, setError] = useState("");
  const [voiceReady, setVoiceReady] = useState(true);
  const [messages, setMessages] = useState<Msg[]>([
    {
      id: "welcome",
      role: "agent",
      text:
        "Namaste — main TrustMesh voice agent hoon. Hold the mic and speak in English, Hindi, or Hinglish. Score ke baare mein poochho, ya bolo “load demo data”. Demo only — not CIBIL.",
    },
  ]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const mediaRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy, listening]);

  useEffect(() => {
    return () => {
      stopTracks();
      try {
        audioRef.current?.pause();
      } catch {
        /* ignore */
      }
    };
  }, []);

  function stopTracks() {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    mediaRef.current = null;
  }

  async function playSarvam(text: string, languageHint?: string | null) {
    try {
      setSpeaking(true);
      const tts = await agentVoiceTts({
        text,
        language_code: languageHint || undefined,
      });
      const src = `data:${tts.mime_type || "audio/wav"};base64,${tts.audio_base64}`;
      if (audioRef.current) {
        audioRef.current.pause();
      }
      const audio = new Audio(src);
      audioRef.current = audio;
      await audio.play();
      await new Promise<void>((resolve) => {
        audio.onended = () => resolve();
        audio.onerror = () => resolve();
      });
    } catch (e) {
      // Soft fallback — never block chat if TTS fails
      setVoiceReady(false);
      if (typeof window !== "undefined" && window.speechSynthesis) {
        window.speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance(text);
        u.lang = /[\u0900-\u097F]/.test(text) || /\b(hai|kya|mera)\b/i.test(text) ? "hi-IN" : "en-IN";
        window.speechSynthesis.speak(u);
      }
      if (e instanceof Error && e.message.includes("not configured")) {
        setError("Sarvam voice not configured on API — text replies still work.");
      }
    } finally {
      setSpeaking(false);
    }
  }

  async function send(text: string, via: "voice" | "text" = "text") {
    const trimmed = text.trim();
    if (!trimmed || busy) return;
    setError("");
    setInput("");
    const userMsg: Msg = { id: `u-${Date.now()}`, role: "user", text: trimmed, via };
    setMessages((m) => [...m, userMsg]);
    setBusy(true);
    try {
      // lang=auto → agent follows EN / HI / Hinglish from the utterance
      const res = await agentChat({ message: trimmed, lang: "auto" });
      const agentMsg: Msg = {
        id: `a-${Date.now()}`,
        role: "agent",
        text: res.reply,
        via,
        meta: { intent: res.intent, tools_used: res.tools_used, score: res.score },
      };
      setMessages((m) => [...m, agentMsg]);
      const ttsLang = res.lang?.startsWith("hi") ? "hi-IN" : undefined;
      await playSarvam(res.reply, ttsLang);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Agent failed");
    } finally {
      setBusy(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void send(input, "text");
  }

  async function startListening() {
    if (busy || listening) return;
    setError("");
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setError("Microphone not available on this device.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          channelCount: 1,
        },
      });
      streamRef.current = stream;
      chunksRef.current = [];
      const mime = pickMime();
      const rec = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
      mediaRef.current = rec;
      rec.ondataavailable = (ev) => {
        if (ev.data.size > 0) chunksRef.current.push(ev.data);
      };
      rec.onstop = () => {
        void finishListening(mime);
      };
      rec.start(200);
      setListening(true);
    } catch {
      setError("Mic permission needed — allow microphone, then hold to speak.");
      stopTracks();
      setListening(false);
    }
  }

  function stopListening() {
    const rec = mediaRef.current;
    if (rec && rec.state !== "inactive") {
      rec.stop();
    } else {
      setListening(false);
      stopTracks();
    }
  }

  async function finishListening(mime: string) {
    setListening(false);
    const blob = new Blob(chunksRef.current, { type: mime || "audio/webm" });
    stopTracks();
    chunksRef.current = [];
    if (blob.size < 800) {
      setError("Too short — hold the mic and speak a bit longer.");
      return;
    }
    setBusy(true);
    try {
      const stt = await agentVoiceStt(blob, mime.includes("mp4") ? "voice.mp4" : "voice.webm");
      const transcript = (stt.transcript || "").trim();
      if (!transcript) {
        setError("Samajh nahi aaya — thoda clear boliye, please.");
        setBusy(false);
        return;
      }
      setBusy(false);
      await send(transcript, "voice");
    } catch (e) {
      setBusy(false);
      setError(e instanceof Error ? e.message : "Voice failed");
    }
  }

  const suggestions = [
    "Mera score explain karo",
    "Explain my trust score",
    "Signals dikhao",
    "Load demo data",
    "Score on-chain hai kya?",
  ];

  return (
    <div className="flex min-h-[calc(100vh-5rem)] flex-col px-4 pb-4 pt-2">
      <PageHeader
        title="Trust Voice Agent"
        description="Hold mic — speak English, Hindi, or Hinglish. Sarvam hears you; answers come only from your TrustMesh tools."
      />

      <div className="mb-3 flex flex-wrap items-center gap-2 text-[11px]">
        <span className="rounded-full border border-wine-500/30 bg-wine-500/10 px-2.5 py-1 font-medium text-wine-400">
          Voice shell · Sarvam
        </span>
        <span className="rounded-full border border-mist-300 px-2.5 py-1 text-zinc-400">
          Grounded chat · no invented reasons
        </span>
        <span className="ml-auto text-zinc-500">
          {listening ? "Listening…" : speaking ? "Speaking…" : voiceReady ? "Ready" : "TTS fallback"}
        </span>
      </div>

      <ErrorText>{error}</ErrorText>

      <div className="flex-1 space-y-3 overflow-y-auto rounded-3xl border border-mist-300 bg-mist-100/40 p-3">
        {messages.map((m) => (
          <FadeUp key={m.id}>
            <div
              className={cn(
                "max-w-[90%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed",
                m.role === "user"
                  ? "ml-auto bg-wine-500 text-white"
                  : "mr-auto border border-white/10 bg-mist-200 text-ink-800",
              )}
            >
              <p>{m.text}</p>
              {m.role === "agent" && m.meta?.tools_used?.length ? (
                <p className="mt-1.5 text-[10px] text-zinc-500">
                  Tools: {m.meta.tools_used.join(", ")}
                  {m.meta.score != null ? ` · score ${m.meta.score}` : ""}
                </p>
              ) : null}
              {m.role === "agent" ? (
                <button
                  type="button"
                  className="mt-1 inline-flex items-center gap-1 text-[10px] font-medium text-wine-400"
                  disabled={busy || speaking}
                  onClick={() => void playSarvam(m.text)}
                >
                  <Volume2 className="h-3 w-3" /> Replay
                </button>
              ) : null}
            </div>
          </FadeUp>
        ))}
        {busy ? <Skeleton className="h-14 w-3/4 rounded-2xl" /> : null}
        <div ref={bottomRef} />
      </div>

      <div className="-mx-1 mt-3 flex gap-2 overflow-x-auto px-1 pb-1 scrollbar-none">
        {suggestions.map((s) => (
          <button
            key={s}
            type="button"
            className="gpay-chip shrink-0 text-left"
            disabled={busy}
            onClick={() => void send(s, "text")}
          >
            {s}
          </button>
        ))}
      </div>

      <div className="mt-4 flex flex-col items-center gap-2">
        <button
          type="button"
          aria-label={listening ? "Release to send" : "Hold to speak"}
          disabled={busy && !listening}
          className={cn(
            "flex h-20 w-20 items-center justify-center rounded-full border-2 transition active:scale-95",
            listening
              ? "animate-soft-pulse border-wine-400 bg-wine-500 text-white shadow-glow"
              : "border-wine-500/40 bg-mist-200 text-wine-400 hover:border-wine-500 hover:bg-mist-300",
          )}
          onPointerDown={(e) => {
            e.preventDefault();
            (e.currentTarget as HTMLButtonElement).setPointerCapture(e.pointerId);
            void startListening();
          }}
          onPointerUp={() => stopListening()}
          onPointerCancel={() => stopListening()}
          onPointerLeave={() => {
            if (listening) stopListening();
          }}
        >
          <Mic className="h-8 w-8" />
        </button>
        <p className="text-center text-[11px] text-zinc-500">
          {listening ? "Release when done…" : "Hold to speak · release to ask"}
        </p>
      </div>

      <form onSubmit={onSubmit} className="mt-3 flex items-end gap-2">
        <input
          className="min-w-0 flex-1 rounded-full border border-mist-300 bg-mist-100 px-4 py-2.5 text-sm outline-none ring-wine-400 focus:ring-2"
          placeholder="Or type in English / Hinglish…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={busy}
        />
        <button type="submit" className={`${btnPrimaryClass} !px-3`} disabled={busy || !input.trim()}>
          <Send className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}
