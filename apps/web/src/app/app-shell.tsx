"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { clearSession, getToken, me as fetchMe } from "@/api";

const nav = [
  { href: "/app", label: "Projects" },
  { href: "/app/jobs", label: "Jobs" },
  { href: "/app/playground", label: "Playground" },
  { href: "/app/settings", label: "Settings" },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const [me, setMe] = useState<{ user?: { email: string }; org?: { name: string; slug: string } } | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/");
      return;
    }
    fetchMe()
      .then(setMe)
      .catch(() => {
        clearSession();
        router.replace("/");
      });
  }, [router]);

  return (
    <div className="min-h-screen grid grid-cols-[220px_1fr]">
      <aside className="border-r border-ink-700 bg-ink-900 px-4 py-6 flex flex-col">
        <Link href="/app" className="font-medium tracking-tight text-lg">
          Finehelper
        </Link>
        <p className="text-xs text-zinc-500 mt-1 mb-8">{me?.org?.slug || "…"}</p>
        <nav className="flex flex-col gap-1 text-sm">
          {nav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`px-2 py-1.5 rounded ${
                path === item.href || (item.href !== "/app" && path.startsWith(item.href))
                  ? "bg-ink-700 text-copper-300"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <button
          className="mt-auto text-left text-xs text-zinc-500 hover:text-zinc-300"
          onClick={() => {
            clearSession();
            router.replace("/");
          }}
        >
          Sign out
        </button>
      </aside>
      <main className="px-8 py-8 max-w-6xl">{children}</main>
    </div>
  );
}
