"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { motion } from "framer-motion";
import { useAuth } from "@/components/providers/auth-provider";
import { PageTransition, Skeleton } from "@/components/motion";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/app", label: "Overview", icon: OverviewIcon },
  { href: "/app/projects", label: "Projects", icon: ProjectsIcon },
  { href: "/app/jobs", label: "Jobs", icon: JobsIcon },
  { href: "/app/deployments", label: "Deployments", icon: DeployIcon },
  { href: "/app/playground", label: "Playground", icon: PlayIcon },
  { href: "/app/settings", label: "Settings", icon: SettingsIcon },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const { status, me, signOut } = useAuth();

  useEffect(() => {
    if (status === "anonymous") router.replace("/");
  }, [status, router]);

  function isActive(href: string) {
    if (href === "/app") return path === "/app";
    if (href === "/app/projects") return path.startsWith("/app/projects");
    return path === href || path.startsWith(`${href}/`);
  }

  if (status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="w-full max-w-sm space-y-3 px-6">
          <Skeleton className="h-8 w-40 mx-auto" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-10 w-full" />
          <p className="text-center text-xs text-zinc-500 animate-soft-pulse">Loading workbench…</p>
        </div>
      </div>
    );
  }

  if (status !== "authenticated") return null;

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[240px_1fr]">
      <aside className="hidden border-r border-mist-300/80 bg-white/60 px-4 py-6 backdrop-blur-md lg:flex lg:flex-col">
        <Link href="/app" className="mb-8 flex items-center gap-2.5 px-2">
          <BrandMark />
          <span className="font-display text-xl text-wine-600">Finehelper</span>
        </Link>
        <p className="mb-4 px-2 text-[11px] font-medium uppercase tracking-wider text-zinc-400">
          {me?.org?.slug || "…"}
        </p>
        <nav className="flex flex-col gap-1 text-sm">
          {nav.map((item) => {
            const active = isActive(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "relative flex items-center gap-2.5 rounded-xl px-3 py-2.5 transition",
                  active ? "text-white" : "text-zinc-600 hover:bg-mist-200/80 hover:text-wine-700",
                )}
              >
                {active && (
                  <motion.span
                    layoutId="nav-pill"
                    className="absolute inset-0 rounded-xl bg-wine-500 shadow-soft"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  />
                )}
                <span className="relative z-10 flex items-center gap-2.5">
                  <Icon className={cn("h-4 w-4", active ? "opacity-100" : "opacity-70")} />
                  {item.label}
                </span>
              </Link>
            );
          })}
        </nav>
        <div className="mt-auto space-y-2 px-1 pt-8">
          <Link
            href="/app/profile"
            className="flex items-center gap-3 rounded-xl border border-mist-300 bg-white/80 px-3 py-2.5 transition hover:bg-mist-100 hover:shadow-lift"
          >
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-wine-100 text-xs font-semibold text-wine-600">
              {(me?.user?.name || me?.user?.email || "?").slice(0, 1).toUpperCase()}
            </span>
            <span className="min-w-0">
              <span className="block truncate text-sm font-medium text-wine-700">{me?.user?.name || "Profile"}</span>
              <span className="block truncate text-[11px] text-zinc-500">{me?.role || "member"}</span>
            </span>
          </Link>
          <button
            className="w-full rounded-xl px-3 py-2 text-left text-xs text-zinc-500 transition hover:bg-mist-200 hover:text-wine-600"
            onClick={signOut}
          >
            Sign out
          </button>
        </div>
      </aside>

      <div className="flex min-h-screen flex-col">
        <header className="sticky top-0 z-20 flex items-center justify-between gap-4 border-b border-mist-300/70 bg-white/70 px-4 py-3 backdrop-blur-md sm:px-8">
          <div className="flex items-center gap-3 lg:hidden">
            <BrandMark />
            <span className="font-display text-lg text-wine-600">Finehelper</span>
          </div>
          <div className="hidden flex-1 lg:block">
            <label className="relative mx-auto block max-w-xl">
              <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400">
                <SearchIcon className="h-4 w-4" />
              </span>
              <input
                className="fh-input pl-10"
                placeholder="Search projects, runs, jobs…"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    const q = (e.target as HTMLInputElement).value.trim();
                    if (q) router.push(`/app/jobs?q=${encodeURIComponent(q)}`);
                  }
                }}
              />
            </label>
          </div>
          <Link
            href="/app/profile"
            className="flex items-center gap-2 rounded-full border border-mist-300 bg-white px-2 py-1.5 text-xs text-zinc-600 transition hover:border-wine-300 hover:shadow-lift"
          >
            <span className="hidden sm:inline">User profile</span>
            <span className="flex h-7 w-7 items-center justify-center rounded-full border border-wine-200 text-wine-500">
              <UserIcon className="h-3.5 w-3.5" />
            </span>
          </Link>
        </header>

        <nav className="flex gap-1 overflow-x-auto border-b border-mist-300/70 bg-white/50 px-3 py-2 lg:hidden">
          {nav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "whitespace-nowrap rounded-lg px-3 py-1.5 text-xs transition",
                isActive(item.href) ? "bg-lagoon-200 text-wine-700" : "text-zinc-500",
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-8">
          <PageTransition>{children}</PageTransition>
        </main>
      </div>
    </div>
  );
}

function BrandMark({ className }: { className?: string }) {
  return (
    <svg className={cn("h-7 w-7 text-wine-500", className)} viewBox="0 0 32 32" fill="none" aria-hidden>
      <circle cx="16" cy="16" r="14" stroke="currentColor" strokeWidth="1.5" opacity="0.35" />
      <circle cx="16" cy="10" r="2.2" fill="currentColor" />
      <circle cx="10" cy="20" r="2.2" fill="currentColor" />
      <circle cx="22" cy="20" r="2.2" fill="currentColor" />
      <path d="M16 12.2L10.8 18.5M16 12.2L21.2 18.5M10.8 20h10.4" stroke="currentColor" strokeWidth="1.4" />
    </svg>
  );
}

function OverviewIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  );
}

function ProjectsIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M4 7h16M4 12h16M4 17h10" strokeLinecap="round" />
    </svg>
  );
}

function JobsIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <circle cx="12" cy="12" r="8" />
      <path d="M12 8v4l2.5 2.5" strokeLinecap="round" />
    </svg>
  );
}

function DeployIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M12 3v12M8 9l4-4 4 4M5 18h14" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function PlayIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M8 5v14l11-7-11-7z" strokeLinejoin="round" />
    </svg>
  );
}

function SettingsIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <circle cx="12" cy="12" r="3" />
      <path d="M12 3v2M12 19v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M3 12h2M19 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" strokeLinecap="round" />
    </svg>
  );
}

function SearchIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <circle cx="11" cy="11" r="6.5" />
      <path d="M16.5 16.5L21 21" strokeLinecap="round" />
    </svg>
  );
}

function UserIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <circle cx="12" cy="9" r="3.5" />
      <path d="M5 19c1.5-3 4-4.5 7-4.5S17.5 16 19 19" strokeLinecap="round" />
    </svg>
  );
}
