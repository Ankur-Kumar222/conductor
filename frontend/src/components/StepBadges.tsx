import type { StepResult } from "../types";

const SERVICE_LABEL: Record<string, string> = { gmail: "Gmail", gcal: "Calendar", drive: "Drive" };

const STATUS_STYLE: Record<string, string> = {
  ok: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  error: "bg-rose-500/15 text-rose-300 border-rose-500/30",
  skipped: "bg-slate-500/15 text-slate-300 border-slate-500/30",
  pending_confirmation: "bg-amber-500/15 text-amber-300 border-amber-500/30",
};

export function StepBadges({ steps }: { steps: StepResult[] }) {
  if (!steps.length) return null;
  return (
    <div className="mt-3 flex flex-wrap gap-1.5">
      {steps.map((s) => (
        <span
          key={s.id}
          title={s.error || s.description}
          className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${
            STATUS_STYLE[s.status] || STATUS_STYLE.skipped
          }`}
        >
          <span className="opacity-70">{SERVICE_LABEL[s.service] || s.service}</span>
          <span className="opacity-50">·</span>
          <span>{s.operation}</span>
          {s.result_count > 0 && <span className="opacity-60">({s.result_count})</span>}
        </span>
      ))}
    </div>
  );
}
