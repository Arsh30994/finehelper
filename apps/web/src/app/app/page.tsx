"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Bot,
  QrCode,
  Send,
  Building2,
  Smartphone,
  Search,
  MoreVertical,
  Nfc,
  ChevronDown,
} from "lucide-react";
import { runTrustDemoFlow } from "@/api";
import { useTrustDashboard } from "@/hooks/use-trust-dashboard";
import { useAuth } from "@/components/providers/auth-provider";
import { Skeleton } from "@/components/motion";
import { ErrorText } from "@/components/ui";
import { useToast } from "@/components/providers/toast-provider";
import { cn } from "@/lib/utils";

const ACTIONS = [
  { href: "/app/scan", label: "Scan any QR code", icon: QrCode },
  { href: "/app/agent", label: "Ask Trust Agent", icon: Bot },
  { href: "/app/signals", label: "Pay anyone", icon: Send, hint: "Demo peers" },
  { href: "/app/onboard", label: "Bank transfer", icon: Building2, hint: "Link demo bank" },
];

export default function TrustHomePage() {
  const router = useRouter();
  const toast = useToast();
  const { me } = useAuth();
  const { data, loading, filling, error, setError, setData } = useTrustDashboard({ autofill: true });
  const [busy, setBusy] = useState(false);
  const [q, setQ] = useState("");

  const score = data?.score;
  const peers = data?.signals_summary?.peers || [];
  const upi = data?.profile?.upi_id || "demo@oksbi";

  const people = useMemo(() => {
    const list = peers.slice(0, 7);
    const filtered = q.trim()
      ? list.filter((p) => p.name.toLowerCase().includes(q.toLowerCase()) || p.upi.includes(q.toLowerCase()))
      : list;
    return filtered;
  }, [peers, q]);

  async function runDemo() {
    setBusy(true);
    setError("");
    try {
      const result = await runTrustDemoFlow({ lang: "en" });
      setData(result.dashboard);
      toast.success(`Trust Score ${result.score.score}`);
      router.push("/app/score");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "failed";
      setError(msg);
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  if (loading || filling) {
    return (
      <div className="space-y-4 p-4">
        <Skeleton className="h-36 w-full rounded-none" />
        <Skeleton className="mx-4 h-24" />
        <Skeleton className="mx-4 h-40" />
      </div>
    );
  }

  return (
    <div className="pb-4">
      {/* Hero landscape + search — GPay style */}
      <div className="relative overflow-hidden fh-mesh px-4 pb-5 pt-4">
        <div className="pointer-events-none absolute inset-0 opacity-50" aria-hidden>
          <svg className="h-full w-full" viewBox="0 0 400 160" preserveAspectRatio="xMidYMid slice">
            <defs>
              <radialGradient id="og" cx="50%" cy="30%" r="60%">
                <stop offset="0%" stopColor="#c29d6d" stopOpacity="0.35" />
                <stop offset="100%" stopColor="#c29d6d" stopOpacity="0" />
              </radialGradient>
            </defs>
            <ellipse cx="200" cy="20" rx="160" ry="50" fill="url(#og)" />
            <rect x="40" y="70" width="36" height="40" rx="6" fill="#c29d6d" opacity="0.15" />
            <rect x="300" y="85" width="48" height="28" rx="8" fill="#d4b483" opacity="0.18" />
            <circle cx="200" cy="100" r="22" fill="#c29d6d" opacity="0.14" />
          </svg>
        </div>
        <div className="relative flex items-center gap-2">
          <label className="flex flex-1 items-center gap-2 rounded-full border border-mist-300 bg-mist-100/90 px-4 py-3 shadow-soft backdrop-blur">
            <Search className="h-4 w-4 text-zinc-400" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search by name or number"
              className="w-full bg-transparent text-sm text-ink-800 outline-none placeholder:text-zinc-500"
            />
          </label>
          <button type="button" className="rounded-full border border-mist-300 bg-mist-100 p-3 shadow-soft" aria-label="More">
            <MoreVertical className="h-4 w-4 text-ink-700" />
          </button>
        </div>
        <p className="relative mt-4 text-center text-[11px] font-medium text-wine-400">
          TrustMesh demo · assumed data · not real UPI
        </p>
      </div>

      <div className="space-y-5 px-4 pt-2">
        <ErrorText>{error}</ErrorText>

        {/* Action grid */}
        <div className="grid grid-cols-4 gap-2">
          {ACTIONS.map((a) => {
            const Icon = a.icon;
            return (
              <Link key={a.label} href={a.href} className="gpay-tile px-1">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-mist-100 text-wine-500 shadow-lift">
                  <Icon className="h-5 w-5" />
                </span>
                <span className="text-[11px] font-medium leading-tight text-ink-800">{a.label}</span>
              </Link>
            );
          })}
        </div>

        {/* Chips */}
        <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 scrollbar-none">
          <Link href="/app/scan" className="gpay-chip">
            <Nfc className="h-3.5 w-3.5 text-wine-500" />
            Tap &amp; Pay
          </Link>
          <Link href="/app/score" className="gpay-chip">
            Trust: {score ? score.score : "—"}/100
          </Link>
          <Link href="/app/agent" className="gpay-chip">
            <Bot className="h-3.5 w-3.5 text-wine-500" />
            Ask agent
          </Link>
          <span className="gpay-chip">UPI ID: {upi}</span>
        </div>

        {/* People */}
        <section>
          <div className="mb-3 flex items-end justify-between">
            <h2 className="text-xl font-semibold text-ink-800">People</h2>
            <Link href="/app/signals" className="text-xs font-medium text-wine-600">
              See signals
            </Link>
          </div>
          <div className="grid grid-cols-4 gap-x-2 gap-y-4">
            {people.map((p, i) => (
              <Link
                key={`${p.upi}-${i}`}
                href={`/app/pay?name=${encodeURIComponent(p.name)}&upi=${encodeURIComponent(p.upi)}&amount=199`}
                className="flex flex-col items-center gap-1.5 text-center"
              >
                <span
                  className={cn(
                    "flex h-14 w-14 items-center justify-center rounded-full text-lg font-semibold text-white",
                    AVATAR_COLORS[i % AVATAR_COLORS.length],
                  )}
                >
                  {p.name.slice(0, 1).toUpperCase()}
                </span>
                <span className="line-clamp-2 text-[11px] font-medium text-ink-700">{p.name.split(" ")[0]}</span>
              </Link>
            ))}
            <Link href="/app/signals" className="flex flex-col items-center gap-1.5 text-center">
              <span className="flex h-14 w-14 items-center justify-center rounded-full border border-mist-300 bg-mist-100 text-wine-500 shadow-lift">
                <ChevronDown className="h-5 w-5" />
              </span>
              <span className="text-[11px] font-medium text-ink-700">More</span>
            </Link>
          </div>
        </section>

        {/* Trust strip */}
        <section className="rounded-3xl border border-white/[0.07] bg-gradient-to-b from-[#161616] to-[#111111] p-4 shadow-soft">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs text-zinc-500">Your Trust Score</p>
              <p className="font-display text-4xl font-semibold text-wine-400">{score?.score ?? "—"}</p>
              {score ? (
                <p className="mt-1 text-xs text-ink-700">
                  Eligible ₹{score.eligibility_min.toLocaleString("en-IN")}–₹
                  {score.eligibility_max.toLocaleString("en-IN")}
                </p>
              ) : null}
            </div>
            <div className="flex flex-col gap-2">
              <Link href="/app/score" className="fh-btn-primary text-xs">
                Open score
              </Link>
              <Link href="/app/offers" className="fh-btn-accent text-xs">
                Offers
              </Link>
            </div>
          </div>
          <button
            type="button"
            className="mt-3 w-full rounded-xl border border-dashed border-wine-500/30 py-2 text-xs font-medium text-wine-400"
            disabled={busy}
            onClick={runDemo}
          >
            {busy ? "Refreshing assumed data…" : "Refresh assumed UPI signals"}
          </button>
          <p className="mt-2 text-center text-[10px] text-zinc-400">
            Hi {me?.user?.name?.split(" ")[0] || "there"} — payments here only log demo signals, no real money.
          </p>
        </section>
      </div>
    </div>
  );
}

const AVATAR_COLORS = [
  "bg-[#3d4f66]", // dusty slate blue
  "bg-[#4a5c4e]", // muted sage
  "bg-[#6b5a3e]", // bronze / antique gold
  "bg-[#6b4545]", // dusty rose
  "bg-[#554c62]", // soft plum
  "bg-[#3f5554]", // muted teal
  "bg-[#4a4a4a]", // warm charcoal gray
];
