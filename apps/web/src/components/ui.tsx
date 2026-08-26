import { cn } from "@/lib/utils";

export function StatusBadge({ status }: { status: string }) {
  const tone =
    status === "succeeded" || status === "ready" || status === "passed" || status === "live"
      ? "bg-lagoon-100 text-lagoon-300"
      : status === "failed" || status === "cancelled"
        ? "bg-red-950 text-red-300"
        : "bg-mist-200 text-zinc-400";
  return (
    <span className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium capitalize", tone)}>
      {status}
    </span>
  );
}

export function EmptyState({ children }: { children: React.ReactNode }) {
  return <p className="p-6 text-sm text-zinc-500">{children}</p>;
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4 animate-fade-up">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight text-white">{title}</h1>
        {description ? <p className="mt-1.5 max-w-xl text-sm text-zinc-500">{description}</p> : null}
      </div>
      {actions}
    </div>
  );
}

export function ErrorText({ children }: { children?: React.ReactNode }) {
  if (!children) return null;
  return <p className="mb-4 break-all text-xs text-red-400">{children}</p>;
}

export function MonoId({ id, chars = 8 }: { id: string; chars?: number }) {
  return <span className="font-mono text-xs text-wine-500">{id.slice(0, chars)}</span>;
}

export function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("fh-card divide-y divide-mist-200 overflow-hidden", className)}>{children}</div>;
}

export function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block text-xs font-semibold text-zinc-300">
      {label}
      <div className="mt-1.5">{children}</div>
    </label>
  );
}

export function MetricRow({
  label,
  hint,
  value,
}: {
  label: string;
  hint?: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-t border-mist-200 py-3 first:border-t-0 first:pt-0">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-wide text-wine-500">{label}</p>
        {hint ? <p className="mt-0.5 text-xs text-zinc-500">{hint}</p> : null}
      </div>
      <p className="font-display text-2xl text-wine-600">{value}</p>
    </div>
  );
}

export const inputClass = "fh-input";
export const btnPrimaryClass = "fh-btn-primary";
export const btnAccentClass = "fh-btn-accent";
export const btnGhostClass = "fh-btn-ghost";
