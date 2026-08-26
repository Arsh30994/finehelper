"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { Bot, Home, IndianRupee, User } from "lucide-react";
import { useAuth } from "@/components/providers/auth-provider";
import { PageTransition, Skeleton } from "@/components/motion";
import { cn } from "@/lib/utils";

/** Home · Trust · Agent · You */
const bottomNav = [
  { href: "/app", label: "Home", icon: Home },
  { href: "/app/score", label: "Trust", icon: IndianRupee },
  { href: "/app/agent", label: "Agent", icon: Bot },
  { href: "/app/profile", label: "You", icon: User },
];

const sideNav = [
  { href: "/app", label: "Home" },
  { href: "/app/agent", label: "Trust Agent" },
  { href: "/app/scan", label: "Scan QR" },
  { href: "/app/signals", label: "People & signals" },
  { href: "/app/score", label: "Trust Score" },
  { href: "/app/offers", label: "Offers" },
  { href: "/app/history", label: "History" },
  { href: "/app/security", label: "Security" },
  { href: "/app/profile", label: "You" },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const { status, signOut } = useAuth();
  const hideChrome = path.startsWith("/app/pay");

  useEffect(() => {
    if (status === "anonymous") router.replace("/");
  }, [status, router]);

  function isActive(href: string) {
    if (href === "/app") return path === "/app";
    return path === href || path.startsWith(`${href}/`);
  }

  if (status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-mist-50">
        <div className="w-full max-w-sm space-y-3 px-6">
          <Skeleton className="mx-auto h-8 w-40" />
          <Skeleton className="h-24 w-full" />
        </div>
      </div>
    );
  }

  if (status !== "authenticated") return null;

  if (hideChrome) {
    return (
      <div className="min-h-screen bg-mist-50">
        <PageTransition>{children}</PageTransition>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-mist-50 lg:grid lg:grid-cols-[220px_1fr]">
      <aside className="hidden border-r border-white/[0.06] bg-[#0e0e0e]/90 px-3 py-6 backdrop-blur-md lg:flex lg:flex-col">
        <Link href="/app" className="mb-8 flex items-center gap-2 px-2">
          <BrandMark />
          <span className="font-display text-lg font-semibold text-white">TrustMesh</span>
        </Link>
        <nav className="flex flex-col gap-0.5 text-sm">
          {sideNav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "rounded-xl px-4 py-2.5 transition",
                isActive(item.href)
                  ? "bg-wine-500/10 font-medium text-wine-400"
                  : "text-zinc-500 hover:bg-white/[0.04] hover:text-ink-800",
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <button
          type="button"
          className="mt-auto rounded-xl px-4 py-2 text-left text-xs text-zinc-600 hover:bg-white/[0.04] hover:text-ink-800"
          onClick={signOut}
        >
          Sign out
        </button>
      </aside>

      <div className="flex min-h-screen flex-col pb-[72px] lg:pb-0">
        <main className="mx-auto w-full max-w-lg flex-1 px-4 pt-4 lg:max-w-2xl lg:px-6">
          <PageTransition>{children}</PageTransition>
        </main>

        <nav className="fixed inset-x-0 bottom-0 z-30 border-t border-white/[0.06] bg-[#111111]/95 backdrop-blur-md lg:hidden">
          <div className="mx-auto flex max-w-lg items-center justify-around px-2 py-2">
            {bottomNav.map((item) => {
              const active = isActive(item.href);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex min-w-[64px] flex-col items-center gap-0.5 rounded-xl px-3 py-1.5 text-[11px] font-medium",
                    active ? "bg-wine-500/10 text-wine-400" : "text-zinc-500",
                  )}
                >
                  <Icon className="h-5 w-5" strokeWidth={active ? 2.2 : 1.7} />
                  {item.label}
                </Link>
              );
            })}
          </div>
        </nav>
      </div>
    </div>
  );
}

function BrandMark({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "flex h-8 w-8 items-center justify-center rounded-xl border border-wine-500/30 bg-gradient-to-br from-[#2a2418] to-[#14110c] text-sm font-semibold text-wine-400",
        className,
      )}
    >
      T
    </span>
  );
}
