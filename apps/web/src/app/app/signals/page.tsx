"use client";

import Link from "next/link";
import { trustBootstrap } from "@/api";
import { useTrustDashboard } from "@/hooks/use-trust-dashboard";
import { FadeUp, Skeleton } from "@/components/motion";
import { ErrorText, PageHeader, btnAccentClass, btnPrimaryClass } from "@/components/ui";

/**
 * Signals = the assumed digital trails the Trust Score reads.
 * Not a wallet: UPI activity, peers, bills, recharges, merchants — all synthetic.
 */
export default function SignalsPage() {
  const { data, loading, filling, error, setData, setError } = useTrustDashboard({ autofill: true });
  const s = data?.signals_summary;

  async function refill() {
    setError("");
    try {
      const d = await trustBootstrap({ force: true, occupation: "kirana", quality: "good" });
      setData(d);
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed");
    }
  }

  if (loading || filling) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-48" />
        <div className="grid grid-cols-3 gap-3">
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
        </div>
        <Skeleton className="h-48 w-full" />
        <p className="text-center text-xs text-zinc-500">Loading assumed payment signals…</p>
      </div>
    );
  }

  return (
    <>
      <PageHeader
        title="Signals"
        description="Assumed UPI, bills, recharges, and peers used to compute your Trust Score — not live bank or wallet data."
      />
      <ErrorText>{error}</ErrorText>

      <div className="mb-4 rounded-2xl border border-amber-200/80 bg-amber-50/70 px-4 py-3 text-xs text-amber-900">
        Everything on this page is synthetic demo data so the product works without real UPI access.
      </div>

      {!s ? (
        <div className="rounded-2xl border border-mist-300 bg-mist-100/90 p-6">
          <p className="text-sm text-zinc-400">No signals loaded yet.</p>
          <button type="button" className={`${btnPrimaryClass} mt-4`} onClick={refill}>
            Load assumed signals
          </button>
        </div>
      ) : (
        <div className="space-y-5">
          <FadeUp className="grid grid-cols-3 gap-3">
            <Stat label="UPI txns" value={s.txn_count} />
            <Stat label="Bills" value={s.bill_count} />
            <Stat label="Recharges" value={s.recharge_count} />
          </FadeUp>

          <Section title="People you pay / get paid by">
            <ul className="divide-y divide-mist-200">
              {(s.peers || []).map((p, i) => (
                <li key={`${p.upi}-${i}`} className="flex justify-between py-3 text-sm">
                  <span>
                    <span className="font-medium text-wine-400">{p.name}</span>
                    <span className="mt-0.5 block text-xs text-zinc-400">{p.upi}</span>
                  </span>
                  <span className="text-xs text-zinc-500">{p.months_known ?? "—"} mo</span>
                </li>
              ))}
            </ul>
          </Section>

          <Section title="Spend categories (assumed)">
            <ul className="flex flex-wrap gap-2">
              {(s.merchants || []).map((m, i) => (
                <li key={`${m.name}-${i}`} className="rounded-full bg-mist-200 px-3 py-1 text-xs text-wine-400">
                  {m.name}
                  {m.txn_count != null
                    ? ` · ${m.txn_count}`
                    : m.count != null
                      ? ` · ${m.count}`
                      : m.spend_total != null
                        ? ` · ₹${Math.round(m.spend_total)}`
                        : ""}
                </li>
              ))}
            </ul>
          </Section>

          <Section title="Bills & recharge">
            <ul className="space-y-2 text-sm">
              {(s.bills || []).slice(0, 8).map((b, i) => (
                <li key={`b-${i}`} className="flex justify-between">
                  <span>{b.provider || b.name || b.kind}</span>
                  <span className={b.on_time ? "text-lagoon-500" : "text-red-600"}>
                    ₹{b.amount} {b.on_time ? "on time" : "late"}
                  </span>
                </li>
              ))}
              {(s.recharges || []).slice(0, 5).map((r, i) => (
                <li key={`r-${i}`} className="flex justify-between text-zinc-500">
                  <span>{r.operator || "Recharge"}</span>
                  <span>₹{r.amount}</span>
                </li>
              ))}
            </ul>
          </Section>

          <div className="flex flex-wrap gap-2">
            <Link href="/app/score" className={btnPrimaryClass}>
              Open Trust Score
            </Link>
            <Link href="/app/history" className={btnAccentClass}>
              Transaction history
            </Link>
            <button type="button" className={btnAccentClass} onClick={refill}>
              Regenerate assumed data
            </button>
          </div>
        </div>
      )}
    </>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-2xl border border-mist-300 bg-mist-100/80 p-4 text-center">
      <p className="font-display text-2xl text-wine-600">{value}</p>
      <p className="text-[11px] uppercase tracking-wide text-zinc-400">{label}</p>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <FadeUp>
      <div className="rounded-2xl border border-mist-300 bg-mist-100/80 p-5">
        <h2 className="mb-3 font-display text-xl text-wine-400">{title}</h2>
        {children}
      </div>
    </FadeUp>
  );
}
