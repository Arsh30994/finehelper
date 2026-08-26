"use client";

import { FormEvent, useEffect, useState } from "react";
import AppShell from "../app-shell";
import { createApiKey, listApiKeys, listCredentials, saveCredential } from "@/api";

type Cred = { id: string; provider: string; last4: string };
type Key = { id: string; name: string; prefix: string };

export default function SettingsPage() {
  const [creds, setCreds] = useState<Cred[]>([]);
  const [keys, setKeys] = useState<Key[]>([]);
  const [newKey, setNewKey] = useState("");
  const [msg, setMsg] = useState("");

  async function load() {
    setCreds(await listCredentials());
    setKeys(await listApiKeys());
  }

  useEffect(() => {
    load().catch((e) => setMsg(String(e.message || e)));
  }, []);

  async function saveCred(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    await saveCredential({ provider: fd.get("provider"), secret: fd.get("secret") });
    (e.target as HTMLFormElement).reset();
    await load();
  }

  async function mintKey() {
    const data = await createApiKey();
    setNewKey(data.key);
    await load();
  }

  return (
    <AppShell>
      <h1 className="text-2xl font-medium mb-8">Settings</h1>
      {msg && <p className="text-xs text-red-400 mb-4">{msg}</p>}
      <section className="mb-10">
        <h2 className="text-sm uppercase tracking-wide text-zinc-500 mb-3">Provider credentials</h2>
        <p className="text-xs text-zinc-500 mb-3">Encrypted at rest. Shown only as last4 after save.</p>
        <form onSubmit={saveCred} className="flex gap-2 mb-4">
          <select name="provider" className="bg-ink-800 border border-ink-700 rounded px-3 py-2 text-sm">
            <option value="openai">openai</option>
            <option value="together">together</option>
            <option value="huggingface">huggingface</option>
          </select>
          <input name="secret" type="password" required placeholder="sk-…" className="bg-ink-800 border border-ink-700 rounded px-3 py-2 text-sm w-64" />
          <button className="text-sm border border-ink-700 rounded px-3">Save</button>
        </form>
        <ul className="text-sm space-y-1">
          {creds.map((c) => (
            <li key={c.id}>
              {c.provider} · ···{c.last4}
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h2 className="text-sm uppercase tracking-wide text-zinc-500 mb-3">CLI / CI API keys</h2>
        <button onClick={mintKey} className="text-sm border border-ink-700 rounded px-3 py-1 mb-3">
          Mint key
        </button>
        {newKey && <p className="text-xs font-mono break-all text-copper-300 mb-3">Shown once: {newKey}</p>}
        <ul className="text-sm space-y-1">
          {keys.map((k) => (
            <li key={k.id}>
              {k.name} · {k.prefix}…
            </li>
          ))}
        </ul>
      </section>
    </AppShell>
  );
}
