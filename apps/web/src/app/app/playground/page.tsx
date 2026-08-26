"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { chatCompletions, listDeployments, listRuns } from "@/api";
import type { Deployment, Run } from "@/types";
import { useToast } from "@/components/providers/toast-provider";
import { ErrorText, btnAccentClass, inputClass } from "@/components/ui";

type Msg = { id: string; role: "assistant" | "user"; content: string };

export default function PlaygroundPage() {
  const toast = useToast();
  const [deps, setDeps] = useState<Deployment[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [deploymentId, setDeploymentId] = useState("");
  const [runId, setRunId] = useState("");
  const [messages, setMessages] = useState<Msg[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Welcome to Finehelper Playground. Pick a deployment or run, then ask anything — responses come from your fine-tune via /v1/chat/completions.",
    },
  ]);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listDeployments().then(setDeps).catch(() => setDeps([]));
    listRuns().then(setRuns).catch(() => setRuns([]));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, pending]);

  async function send(text: string) {
    if (!text.trim() || pending) return;
    if (!deploymentId && !runId) {
      toast.info("Select a deployment or run first");
      return;
    }
    setError("");
    setPending(true);
    const userMsg: Msg = { id: `u-${Date.now()}`, role: "user", content: text };
    setMessages((m) => [...m, userMsg]);
    try {
      const data = await chatCompletions({
        deployment_id: deploymentId || null,
        run_id: runId || null,
        messages: [{ role: "user", content: text }],
      });
      setMessages((m) => [
        ...m,
        { id: `a-${Date.now()}`, role: "assistant", content: data.choices[0].message.content },
      ]);
    } catch (err) {
      const message = err instanceof Error ? err.message : "chat failed";
      setError(message);
      toast.error("Chat request failed");
    } finally {
      setPending(false);
    }
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const text = String(fd.get("message") || "");
    (e.target as HTMLFormElement).reset();
    await send(text);
  }

  const suggestions = [
    { label: "Explain this model’s specialty", text: "What kinds of questions are you best at answering?" },
    { label: "Smoke-test tone", text: "Reply in one short helpful sentence as if you are the production assistant." },
  ];

  return (
    <div className="mx-auto flex h-[calc(100vh-8rem)] max-w-3xl flex-col">
      <header className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl text-wine-600">Support & Guidance</h1>
          <p className="text-sm text-zinc-500">Chat against a run or deployment</p>
        </div>
      </header>

      <div className="mb-4 grid gap-2 sm:grid-cols-2">
        <select
          className={inputClass}
          value={deploymentId}
          onChange={(e) => {
            setDeploymentId(e.target.value);
            setRunId("");
          }}
        >
          <option value="">Deployment —</option>
          {deps.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name} ({d.backend})
            </option>
          ))}
        </select>
        <select
          className={inputClass}
          value={runId}
          onChange={(e) => {
            setRunId(e.target.value);
            setDeploymentId("");
          }}
        >
          <option value="">Or run —</option>
          {runs.map((r) => (
            <option key={r.id} value={r.id}>
              {r.id.slice(0, 8)} {r.backend} {r.provider_model_id || ""}
            </option>
          ))}
        </select>
      </div>

      <div className="fh-card relative flex min-h-0 flex-1 flex-col overflow-hidden">
        <div className="flex-1 space-y-4 overflow-y-auto px-4 py-5 sm:px-6">
          <div className="flex justify-center">
            <span className="rounded-full bg-mist-200 px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
              Today
            </span>
          </div>

          <AnimatePresence initial={false}>
            {messages.map((m) =>
              m.role === "assistant" ? (
                <motion.div
                  key={m.id}
                  initial={{ opacity: 0, y: 10, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ type: "spring", stiffness: 380, damping: 28 }}
                  className="flex items-start gap-3"
                >
                  <span className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-wine-500 text-white">
                    <SparkIcon />
                  </span>
                  <div className="max-w-[85%] rounded-2xl border border-mist-300 bg-white px-4 py-3 font-display text-[15px] leading-relaxed text-wine-800 shadow-sm">
                    {m.content}
                  </div>
                </motion.div>
              ) : (
                <motion.div
                  key={m.id}
                  initial={{ opacity: 0, y: 10, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ type: "spring", stiffness: 380, damping: 28 }}
                  className="flex justify-end"
                >
                  <div className="max-w-[80%] rounded-2xl rounded-br-md bg-wine-500 px-4 py-3 font-display text-[15px] leading-relaxed text-white shadow-soft">
                    {m.content}
                  </div>
                </motion.div>
              ),
            )}
          </AnimatePresence>

          {messages.length === 1 && (
            <div className="ml-11 flex flex-col gap-2">
              {suggestions.map((s) => (
                <motion.button
                  key={s.label}
                  type="button"
                  whileHover={{ x: 4 }}
                  whileTap={{ scale: 0.98 }}
                  className={`${btnAccentClass} justify-start text-left text-xs uppercase tracking-wide`}
                  onClick={() => send(s.text)}
                >
                  {s.label}
                </motion.button>
              ))}
            </div>
          )}

          {pending && (
            <div className="flex items-center gap-3 text-sm text-zinc-500">
              <motion.span
                className="h-8 w-8 rounded-full bg-wine-100"
                animate={{ opacity: [0.5, 1, 0.5], scale: [0.95, 1, 0.95] }}
                transition={{ repeat: Infinity, duration: 1.2 }}
              />
              Thinking…
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="border-t border-mist-200 bg-white/80 p-4 backdrop-blur">
          <ErrorText>{error}</ErrorText>
          <form onSubmit={onSubmit} className="flex gap-2">
            <input
              name="message"
              required
              disabled={pending}
              className={`${inputClass} flex-1`}
              placeholder="Ask a question about your fine-tune…"
              autoComplete="off"
            />
            <motion.button
              type="submit"
              disabled={pending}
              className="fh-btn-primary aspect-square px-3"
              aria-label="Send"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.94 }}
            >
              <SendIcon />
            </motion.button>
          </form>
          <p className="mt-3 text-center text-[10px] uppercase tracking-wider text-zinc-400">
            Finehelper playground streams OpenAI-compatible completions from your org credentials
          </p>
        </div>
      </div>
    </div>
  );
}

function SparkIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2l1.2 6.3L19 12l-5.8 3.7L12 22l-1.2-6.3L5 12l5.8-3.7L12 2z" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
