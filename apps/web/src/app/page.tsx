"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { login, setSession, signup } from "@/api";

export default function HomePage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setPending(true);
    const fd = new FormData(e.currentTarget);
    try {
      const data =
        mode === "login"
          ? await login({ email: String(fd.get("email")), password: String(fd.get("password")) })
          : await signup({
              email: String(fd.get("email")),
              password: String(fd.get("password")),
              name: String(fd.get("name")),
              org_name: String(fd.get("org_name")),
            });
      setSession(data.token, data.org);
      router.push("/app");
    } catch (err) {
      setError(err instanceof Error ? err.message : "failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="min-h-screen grid md:grid-cols-2">
      <section className="hidden md:flex flex-col justify-between p-12 border-r border-ink-700 bg-ink-900">
        <div>
          <p className="text-copper-400 text-sm tracking-wide">FINEHELPER</p>
          <h1 className="mt-10 text-4xl leading-tight font-medium max-w-md">
            Raw examples in.
            <br />
            An evaluated model out.
          </h1>
          <p className="mt-6 text-zinc-400 max-w-sm text-sm leading-relaxed">
            Version datasets, train on OpenAI or LoRA, gate on a golden suite, then deploy behind one OpenAI-compatible
            endpoint.
          </p>
        </div>
        <ol className="text-sm text-zinc-500 space-y-2">
          <li>1. Ingest canonical chat JSONL</li>
          <li>2. Train via provider API or QLoRA</li>
          <li>3. Eval before promote</li>
        </ol>
      </section>
      <section className="flex items-center justify-center p-8">
        <form onSubmit={onSubmit} className="w-full max-w-sm space-y-4">
          <h2 className="text-xl font-medium">{mode === "login" ? "Sign in" : "Create workspace"}</h2>
          {mode === "signup" && (
            <>
              <label className="block text-xs text-zinc-500">
                Name
                <input name="name" required className="mt-1 w-full bg-ink-800 border border-ink-700 rounded px-3 py-2 text-sm" />
              </label>
              <label className="block text-xs text-zinc-500">
                Organization
                <input name="org_name" required className="mt-1 w-full bg-ink-800 border border-ink-700 rounded px-3 py-2 text-sm" />
              </label>
            </>
          )}
          <label className="block text-xs text-zinc-500">
            Email
            <input name="email" type="email" required className="mt-1 w-full bg-ink-800 border border-ink-700 rounded px-3 py-2 text-sm" />
          </label>
          <label className="block text-xs text-zinc-500">
            Password
            <input name="password" type="password" minLength={8} required className="mt-1 w-full bg-ink-800 border border-ink-700 rounded px-3 py-2 text-sm" />
          </label>
          {error && <p className="text-xs text-red-400 break-all">{error}</p>}
          <button disabled={pending} className="w-full bg-copper-500 hover:bg-copper-400 text-ink-950 text-sm font-medium rounded py-2">
            {pending ? "Working…" : mode === "login" ? "Continue" : "Create account"}
          </button>
          <button
            type="button"
            className="w-full text-xs text-zinc-500"
            onClick={() => setMode(mode === "login" ? "signup" : "login")}
          >
            {mode === "login" ? "Need an account? Sign up" : "Have an account? Sign in"}
          </button>
        </form>
      </section>
    </div>
  );
}
