"use client";

import Link from "next/link";
import { ArrowLeft, Zap, Gift, CalendarDays } from "lucide-react";
import { useTrustDashboard } from "@/hooks/use-trust-dashboard";
import { Skeleton } from "@/components/motion";
import { btnPrimaryClass } from "@/components/ui";

export default function OffersPage() {
  const { data, loading, filling } = useTrustDashboard({ autofill: true });
  if (loading || filling) return <Skeleton className="m-4 h-64" />;
  const score = data?.score;
  const max = score?.eligibility_max ?? 50000;

  return (
    <div className="bg-mist-100 pb-10">
      <div className="flex items-center justify-between px-4 py-3">
        <Link href="/app" className="rounded-full p-2 hover:bg-mist-100">
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <span className="text-[11px] text-zinc-400">Sponsored · demo</span>
      </div>

      <div className="fh-mesh mx-4 overflow-hidden rounded-3xl px-5 pb-6 pt-8">
        <p className="text-sm font-semibold text-ink-800">
          Flex <span className="font-normal text-zinc-500">by TrustMesh</span>
        </p>
        <h1 className="mt-6 text-center text-2xl font-semibold leading-snug text-ink-800">
          Credit simplified by TrustMesh
        </h1>
        <div className="mt-6 grid grid-cols-3 gap-3 text-center">
          <Feature icon={<Zap className="h-5 w-5 text-wine-500" />} label="Get limit instantly" />
          <Feature icon={<Gift className="h-5 w-5 text-copper-500" />} label="Earn demo rewards" />
          <Feature icon={<CalendarDays className="h-5 w-5 text-lagoon-500" />} label="Flexible EMIs" />
        </div>
      </div>

      <div className="mx-4 mt-5 rounded-3xl bg-[#e6f4ea] p-5">
        <h2 className="text-lg font-semibold text-ink-800">Free forever, pay anywhere like UPI</h2>
        <p className="mt-2 text-sm text-ink-700">
          From kiranas to malls — assumed eligibility from your Trust Score. Not a real card or lender.
        </p>
      </div>

      <div className="mx-4 mt-5 rounded-3xl border border-mist-300 p-4">
        <h2 className="text-xl font-semibold text-ink-800">
          Loans up to ₹{Math.max(max, 100000).toLocaleString("en-IN")}
        </h2>
        <p className="mt-1 text-sm text-zinc-500">100% digital demo. Assumed money in account — not real disbursal.</p>
        <ul className="mt-4 space-y-3">
          <Detail label="Loan amount" value={`₹${(score?.eligibility_min ?? 100).toLocaleString("en-IN")} to ₹${max.toLocaleString("en-IN")}`} />
          <Detail label="Interest rate" value="Starting at 9.99% per year (demo)" />
          <Detail label="Loan period" value="6 months to 6 years (demo)" />
        </ul>
        <button type="button" className={`${btnPrimaryClass} mt-5 w-full`} disabled>
          Demo only
        </button>
      </div>

      {/* Rewards-style grid */}
      <div className="mx-4 mt-6">
        <h2 className="mb-3 text-lg font-semibold text-ink-800">Rewards</h2>
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-2xl bg-wine-500 p-4 text-white shadow-lift">
            <p className="text-2xl font-bold">₹10</p>
            <p className="text-xs opacity-90">Cashback · assumed</p>
          </div>
          <div className="rounded-2xl bg-copper-400 p-4 text-ink-800 shadow-lift">
            <p className="text-sm font-semibold">15% off</p>
            <p className="text-xs">Demo partner meal</p>
          </div>
          <div className="rounded-2xl border border-mist-300 bg-mist-100 p-4 shadow-lift">
            <p className="text-sm font-semibold text-ink-800">₹450 off</p>
            <p className="text-xs text-zinc-500">CODE DEMO3118</p>
          </div>
          <div className="rounded-2xl bg-[#ea4335] p-4 text-white shadow-lift">
            <p className="text-2xl font-bold">?</p>
            <p className="text-xs opacity-90">Scratch card</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function Feature({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <div className="flex flex-col items-center gap-2">
      <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-mist-100 shadow-lift">{icon}</span>
      <span className="text-[11px] font-medium leading-tight text-ink-700">{label}</span>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <li className="flex items-start gap-3">
      <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-mist-200 text-xs font-bold text-wine-600">
        ₹
      </span>
      <span>
        <span className="block text-[11px] text-zinc-500">{label}</span>
        <span className="block text-sm font-semibold text-ink-800">{value}</span>
      </span>
    </li>
  );
}
