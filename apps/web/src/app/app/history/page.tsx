"use client";

import Link from "next/link";
import { useTrustDashboard } from "@/hooks/use-trust-dashboard";
import { FadeUp, Skeleton } from "@/components/motion";
import { PageHeader } from "@/components/ui";

export default function HistoryPage() {
  const { data, loading, filling } = useTrustDashboard({ autofill: true });

  if (loading || filling) return <Skeleton className="h-64 w-full" />;
  const txns = data?.signals_summary?.recent_txns || [];

  return (
    <>
      <PageHeader
        title="History"
        description="Recent assumed UPI signal feed used by the model — not a bank statement."
      />
      {!txns.length ? (
        <p className="text-sm text-zinc-500">
          Empty. Open{" "}
          <Link href="/app/score" className="text-wine-600 underline">
            Score
          </Link>{" "}
          to load assumed data.
        </p>
      ) : (
        <FadeUp>
          <ul className="divide-y divide-mist-200 overflow-hidden rounded-2xl border border-mist-300 bg-mist-100/90">
            {txns.map((t, i) => (
              <li key={`${t.at}-${i}`} className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
                <div className="min-w-0">
                  <p className="truncate font-medium text-wine-400">{t.counterparty || t.note || "UPI"}</p>
                  <p className="text-[11px] text-zinc-400">{t.at?.slice(0, 16)?.replace("T", " ")}</p>
                </div>
                <p className={t.direction === "in" ? "text-lagoon-500" : "text-wine-600"}>
                  {t.direction === "in" ? "+" : "−"}₹{Number(t.amount).toLocaleString("en-IN")}
                </p>
              </li>
            ))}
          </ul>
        </FadeUp>
      )}
    </>
  );
}
