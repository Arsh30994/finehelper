"use client";

import { FormEvent, useEffect, useState } from "react";
import { createApiKey, listApiKeys, listCredentials, saveCredential } from "@/api";
import type { ApiKey, Credential } from "@/types";
import { useToast } from "@/components/providers/toast-provider";
import { FadeUp } from "@/components/motion";
import { ErrorText, PageHeader, btnGhostClass, btnPrimaryClass, inputClass } from "@/components/ui";

export default function SettingsPage() {
  const toast = useToast();
  const [creds, setCreds] = useState<Credential[]>([]);
  const [keys, setKeys] = useState<ApiKey[]>([]);
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
    try {
      await saveCredential({ provider: fd.get("provider"), secret: fd.get("secret") });
      (e.target as HTMLFormElement).reset();
      await load();
      toast.success("Credential saved");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Save failed");
    }
  }

  async function mintKey() {
    try {
      const data = await createApiKey();
      setNewKey(data.key);
      await load();
      toast.success("API key minted — copy it now");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Mint failed");
    }
  }

  return (
    <>
      <PageHeader title="Settings" description="Provider secrets and CLI keys for this organization." />
      <ErrorText>{msg}</ErrorText>

      <FadeUp>
        <section className="fh-card mb-6 p-6">
          <h2 className="font-display text-xl text-wine-600">Provider credentials</h2>
          <p className="mt-1 text-xs text-zinc-500">Encrypted at rest. Shown only as last4 after save.</p>
          <form onSubmit={saveCred} className="mt-4 flex flex-wrap gap-2">
            <select name="provider" className={`${inputClass} w-auto`}>
              <option value="openai">openai</option>
              <option value="together">together</option>
              <option value="huggingface">huggingface</option>
            </select>
            <input name="secret" type="password" required placeholder="sk-…" className={`${inputClass} w-64`} />
            <button className={btnPrimaryClass}>Save credential</button>
          </form>
          <ul className="mt-5 space-y-2">
            {creds.map((c) => (
              <li key={c.id} className="flex items-center justify-between rounded-xl bg-mist-100 px-4 py-2.5 text-sm">
                <span className="font-medium capitalize text-wine-700">{c.provider}</span>
                <span className="font-mono text-xs text-zinc-500">···{c.last4}</span>
              </li>
            ))}
            {creds.length === 0 && <li className="text-sm text-zinc-500">No credentials stored yet.</li>}
          </ul>
        </section>
      </FadeUp>

      <FadeUp delay={0.08}>
        <section className="fh-card p-6">
          <h2 className="font-display text-xl text-wine-600">CLI / CI API keys</h2>
          <p className="mt-1 text-xs text-zinc-500">Mint a key for the Finehelper CLI or CI pipelines.</p>
          <button onClick={mintKey} className={`${btnGhostClass} mt-4`}>
            Mint key
          </button>
          {newKey && (
            <p className="mt-3 break-all rounded-xl bg-lagoon-100 px-4 py-3 font-mono text-xs text-wine-700">
              Shown once: {newKey}
            </p>
          )}
          <ul className="mt-4 space-y-2">
            {keys.map((k) => (
              <li key={k.id} className="flex items-center justify-between rounded-xl bg-mist-100 px-4 py-2.5 text-sm">
                <span>{k.name}</span>
                <span className="font-mono text-xs text-zinc-500">{k.prefix}…</span>
              </li>
            ))}
          </ul>
        </section>
      </FadeUp>
    </>
  );
}
