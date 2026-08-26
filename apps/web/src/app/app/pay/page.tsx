"use client";

import { Suspense, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { X, ChevronRight } from "lucide-react";
import { trustScan } from "@/api";
import { useToast } from "@/components/providers/toast-provider";
import { btnPrimaryClass } from "@/components/ui";

function PayInner() {
  const params = useSearchParams();
  const router = useRouter();
  const toast = useToast();
  const name = params.get("name") || "Demo peer";
  const upi = params.get("upi") || "demo@oksbi";
  const initialAmount = params.get("amount") || "199";
  const [amount, setAmount] = useState(initialAmount);
  const [note, setNote] = useState("Thanks!");
  const [busy, setBusy] = useState(false);

  const avatar = useMemo(() => name.slice(0, 1).toUpperCase(), [name]);

  async function confirm() {
    setBusy(true);
    try {
      const raw = `upi://pay?pa=${encodeURIComponent(upi)}&pn=${encodeURIComponent(name)}&am=${encodeURIComponent(amount)}&cu=INR&tn=${encodeURIComponent(note)}`;
      await trustScan(raw, Number(amount) || undefined);
      toast.success("Logged as assumed signal — no money moved");
      router.push("/app/history");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-lg flex-col bg-mist-100 px-4 pb-8 pt-3">
      <div className="flex items-center justify-between">
        <Link href="/app" className="rounded-full p-2 hover:bg-mist-100" aria-label="Close">
          <X className="h-5 w-5" />
        </Link>
        <span className="text-[11px] text-zinc-400">Demo pay · no settlement</span>
      </div>

      <div className="mt-10 flex flex-1 flex-col items-center text-center">
        <div className="flex h-20 w-20 items-center justify-center rounded-full bg-wine-500 text-3xl font-semibold text-white">
          {avatar}
        </div>
        <p className="mt-4 text-sm text-zinc-500">Paying to {name}</p>
        <div className="mt-4 flex items-baseline justify-center gap-1">
          <span className="text-3xl font-medium text-ink-800">₹</span>
          <input
            className="w-40 bg-transparent text-center font-display text-5xl text-ink-800 outline-none"
            value={amount}
            onChange={(e) => setAmount(e.target.value.replace(/[^\d.]/g, ""))}
            inputMode="decimal"
          />
        </div>
        <button
          type="button"
          className="mt-4 rounded-full bg-mist-200 px-4 py-1.5 text-sm text-wine-400"
          onClick={() => setNote((n) => (n === "Thanks!" ? "Assumed demo" : "Thanks!"))}
        >
          {note}
        </button>
      </div>

      <button
        type="button"
        className="mb-3 flex w-full items-center gap-3 rounded-2xl border border-mist-300 bg-mist-100 p-4 text-left shadow-lift"
        onClick={() => router.push("/app/onboard")}
      >
        <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-mist-200 text-xs font-bold text-wine-400">
          Bank
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-medium text-ink-800">Your bank ···· 4242</span>
          <span className="block truncate text-xs text-zinc-500">{upi}</span>
        </span>
        <ChevronRight className="h-4 w-4 text-zinc-400" />
      </button>

      <button type="button" className={`${btnPrimaryClass} w-full py-3`} disabled={busy} onClick={confirm}>
        {busy ? "Logging…" : "Confirm (demo signal)"}
      </button>
    </div>
  );
}

export default function PayPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-sm text-zinc-500">Loading…</div>}>
      <PayInner />
    </Suspense>
  );
}
