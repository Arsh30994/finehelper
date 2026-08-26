"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ShieldCheck } from "lucide-react";
import { trustAttest, trustAttestVerify, trustBootstrap, trustExplain } from "@/api";
import { factorPercent, useTrustDashboard } from "@/hooks/use-trust-dashboard";
import { FadeUp, Skeleton } from "@/components/motion";
import { ErrorText, PageHeader, btnAccentClass, btnPrimaryClass } from "@/components/ui";

const FACTOR_COPY: Record<string, string> = {
  payment_consistency: "Bills & recharges paid on a steady rhythm",
  transaction_volume: "Healthy UPI activity over the last 6 months",
  network_stability: "Repeating peers / suppliers you already know",
  income_regularity: "Recurring inflows that look income-like",
};

export default function ScorePage() {
  const { data, loading, filling, error, setData, setError, refresh } = useTrustDashboard({ autofill: true });
  const [explanation, setExplanation] = useState("");
  const [lang, setLang] = useState<"en" | "hi">("en");
  const [busy, setBusy] = useState(false);
  const [chainMsg, setChainMsg] = useState("");
  const [chainOk, setChainOk] = useState<boolean | null>(null);

  const score = data?.score;

  useEffect(() => {
    if (!score) return;
    if (score.explanation) setExplanation(score.explanation);
    trustExplain(lang)
      .then((ex) => setExplanation(ex.explanation))
      .catch(() => undefined);
  }, [score?.id, lang]);

  useEffect(() => {
    if (!score) return;
    if (score.chain_tx_hash) {
      setChainOk(true);
      return;
    }
    trustAttestVerify()
      .then((v) => {
        setChainOk(v.ok);
        if (v.ok) void refresh();
      })
      .catch(() => setChainOk(false));
  }, [score?.id, score?.chain_tx_hash, refresh]);

  async function refill() {
    setBusy(true);
    setError("");
    try {
      const d = await trustBootstrap({ occupation: "kirana", quality: "good", force: true, lang });
      setData(d);
      if (d.score?.explanation) setExplanation(d.score.explanation);
      setChainOk(Boolean(d.score?.chain_tx_hash));
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed");
    } finally {
      setBusy(false);
    }
  }

  async function anchorChain() {
    setBusy(true);
    setChainMsg("");
    try {
      const res = await trustAttest();
      if (res.score) {
        setData({ ...(data || { profile: null, signals_summary: null }), score: res.score });
      }
      setChainOk(true);
      setChainMsg(
        `Anchored on ${res.attestation.network || "local"} · block ${res.attestation.block_number ?? "—"}`,
      );
    } catch (e) {
      setChainOk(false);
      setChainMsg(e instanceof Error ? e.message : "attest failed");
    } finally {
      setBusy(false);
    }
  }

  async function verifyChain() {
    setBusy(true);
    setChainMsg("");
    try {
      const v = await trustAttestVerify();
      setChainOk(v.ok);
      setChainMsg(v.ok ? "Hash matches ledger — fingerprint intact." : "Verification failed — re-anchor recommended.");
      if (v.ok) void refresh();
    } catch (e) {
      setChainOk(false);
      setChainMsg(e instanceof Error ? e.message : "verify failed");
    } finally {
      setBusy(false);
    }
  }

  if (loading || filling) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-56" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-40 w-full" />
        <p className="text-center text-xs text-zinc-500">Loading assumed Trust Score…</p>
      </div>
    );
  }

  const txShort = score?.chain_tx_hash
    ? `${score.chain_tx_hash.slice(0, 10)}…${score.chain_tx_hash.slice(-6)}`
    : null;

  return (
    <>
      <PageHeader
        title="Trust Score"
        description="Thin-file score from assumed UPI, bill, and recharge patterns — not CIBIL. Demo only."
      />
      <ErrorText>{error}</ErrorText>

      {!score ? (
        <div className="rounded-2xl border border-mist-300 bg-mist-100/90 p-6">
          <p className="text-sm text-zinc-400">No score yet. Fill with assumed kirana demo data.</p>
          <button type="button" className={`${btnPrimaryClass} mt-4`} disabled={busy} onClick={refill}>
            {busy ? "Generating…" : "Generate assumed score"}
          </button>
        </div>
      ) : (
        <div className="space-y-5">
          <FadeUp>
            <div className="relative overflow-hidden rounded-3xl border border-white/[0.07] bg-gradient-to-b from-[#1a1712] to-[#111111] p-6 text-center shadow-soft sm:p-8">
              <div className="pointer-events-none absolute -right-8 -top-12 h-40 w-40 rounded-full bg-wine-500/[0.12] blur-3xl" aria-hidden />
              <p className="relative text-[11px] font-medium uppercase tracking-[0.14em] text-wine-500">Assumed demo score</p>
              <motion.p
                className="relative mt-2 font-display text-7xl font-semibold leading-none text-wine-400 sm:text-8xl"
                initial={{ scale: 0.92, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
              >
                {score.score}
              </motion.p>
              <p className="relative mt-2 text-sm text-zinc-500">out of 100 · model {score.model_version || "v1"}</p>
              <div className="relative mt-4 inline-flex rounded-full border border-wine-500/25 bg-wine-500/10 px-4 py-1.5 text-sm font-medium text-wine-400">
                Eligible ₹{score.eligibility_min.toLocaleString("en-IN")} – ₹
                {score.eligibility_max.toLocaleString("en-IN")}
              </div>
              <p className="relative mt-3 text-[11px] text-zinc-600">
                Band is productized eligibility for the demo — not a real loan offer.
              </p>
            </div>
          </FadeUp>

          <FadeUp>
            <div className="rounded-2xl border border-mist-300 bg-mist-100/90 p-5">
              <div className="mb-2 flex items-center gap-2">
                <ShieldCheck className={`h-5 w-5 ${chainOk ? "text-wine-600" : "text-zinc-400"}`} />
                <h2 className="font-display text-xl text-wine-400">On-chain attestation</h2>
              </div>
              <p className="text-sm text-zinc-400">
                Fingerprint of your score (hash + Merkle root of signals) is anchored on a local hash-linked
                ledger
                {score.chain_mode?.includes("evm") ? " and optional Polygon" : ""}. No raw UPI or PII
                on-chain.
              </p>
              <dl className="mt-3 space-y-1.5 text-xs text-ink-700">
                <div className="flex justify-between gap-3">
                  <dt className="text-zinc-500">Network</dt>
                  <dd className="font-medium">{score.chain_network || "local"}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-zinc-500">Tx</dt>
                  <dd className="font-mono">{txShort || "not anchored yet"}</dd>
                </div>
                {score.score_hash ? (
                  <div className="flex justify-between gap-3">
                    <dt className="text-zinc-500">Score hash</dt>
                    <dd className="max-w-[60%] truncate font-mono" title={score.score_hash}>
                      {score.score_hash.slice(0, 14)}…
                    </dd>
                  </div>
                ) : null}
                {score.chain_block != null ? (
                  <div className="flex justify-between gap-3">
                    <dt className="text-zinc-500">Block</dt>
                    <dd className="font-medium">{score.chain_block}</dd>
                  </div>
                ) : null}
              </dl>
              {chainMsg ? <p className="mt-2 text-xs text-wine-600">{chainMsg}</p> : null}
              <div className="mt-3 flex flex-wrap gap-2">
                <button type="button" className={btnPrimaryClass} disabled={busy} onClick={verifyChain}>
                  Verify
                </button>
                <button type="button" className={btnAccentClass} disabled={busy} onClick={anchorChain}>
                  Re-anchor
                </button>
                {score.chain_explorer_url ? (
                  <a
                    href={score.chain_explorer_url}
                    target="_blank"
                    rel="noreferrer"
                    className={btnAccentClass}
                  >
                    Explorer
                  </a>
                ) : null}
              </div>
            </div>
          </FadeUp>

          <FadeUp>
            <div className="rounded-2xl border border-mist-300 bg-mist-100/90 p-5">
              <h2 className="mb-4 font-display text-xl text-wine-400">Why this score</h2>
              <ul className="space-y-4">
                {Object.entries(score.factors || {}).map(([k, v]) => {
                  const pct = factorPercent(v);
                  return (
                    <li key={k}>
                      <div className="mb-1 flex items-end justify-between gap-3">
                        <div>
                          <p className="text-sm font-medium capitalize text-wine-400">{k.replaceAll("_", " ")}</p>
                          <p className="text-[11px] text-zinc-400">{FACTOR_COPY[k] || "Contributes to thin-file trust"}</p>
                        </div>
                        <span className="font-display text-lg text-wine-600">{pct}</span>
                      </div>
                      <div className="h-2.5 overflow-hidden rounded-full bg-mist-200">
                        <motion.div
                          className="h-full rounded-full bg-wine-500"
                          initial={{ width: 0 }}
                          animate={{ width: `${pct}%` }}
                          transition={{ duration: 0.55 }}
                        />
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          </FadeUp>

          <FadeUp>
            <div className="rounded-2xl border border-mist-300 bg-mist-100/90 p-5">
              <div className="mb-2 flex items-center justify-between gap-2">
                <h2 className="font-display text-xl text-wine-400">Plain-language explanation</h2>
                <div className="flex gap-2 text-xs">
                  <button
                    type="button"
                    className={lang === "en" ? "font-semibold text-wine-600" : "text-zinc-400"}
                    onClick={() => setLang("en")}
                  >
                    English
                  </button>
                  <span className="text-zinc-300">|</span>
                  <button
                    type="button"
                    className={lang === "hi" ? "font-semibold text-wine-600" : "text-zinc-400"}
                    onClick={() => setLang("hi")}
                  >
                    Hinglish
                  </button>
                </div>
              </div>
              <p className="text-sm leading-relaxed text-zinc-400">
                {explanation || "Generating explanation from assumed factors…"}
              </p>
            </div>
          </FadeUp>

          <div className="flex flex-wrap gap-2">
            <Link href="/app/offers" className={btnPrimaryClass}>
              See offers
            </Link>
            <Link href="/app/signals" className={btnAccentClass}>
              View signals
            </Link>
            <button type="button" className={btnAccentClass} disabled={busy} onClick={refill}>
              {busy ? "Refreshing…" : "Regenerate assumed data"}
            </button>
          </div>
        </div>
      )}
    </>
  );
}
