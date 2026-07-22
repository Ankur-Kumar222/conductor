import { useState } from "react";
import type { PendingConfirmation } from "../types";

const ACTION_LABEL: Record<string, string> = {
  send_email: "Send email",
  create_event: "Create event",
  update_event: "Update event",
  delete_event: "Delete event",
  share_file: "Share file",
};

export function PendingActionCard({
  action,
  onConfirm,
  onCancel,
}: {
  action: PendingConfirmation;
  onConfirm: (id: string) => Promise<void>;
  onCancel: (id: string) => Promise<void>;
}) {
  const [state, setState] = useState<"idle" | "working" | "confirmed" | "cancelled">("idle");

  const run = async (fn: (id: string) => Promise<void>, next: "confirmed" | "cancelled") => {
    setState("working");
    try {
      await fn(action.action_id);
      setState(next);
    } catch {
      setState("idle");
    }
  };

  return (
    <div className="mt-3 rounded-xl border border-amber-500/30 bg-amber-500/5 p-3">
      <div className="mb-1 flex items-center gap-2 text-xs font-semibold text-amber-300">
        <span className="inline-block h-1.5 w-1.5 rounded-full bg-amber-400" />
        Awaiting confirmation · {ACTION_LABEL[action.action_type] || action.action_type}
      </div>
      <pre className="max-h-56 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-black/30 p-3 text-[12.5px] leading-relaxed text-slate-200">
        {action.preview}
      </pre>
      {state === "confirmed" ? (
        <div className="mt-2 text-xs font-medium text-emerald-300">✓ Done</div>
      ) : state === "cancelled" ? (
        <div className="mt-2 text-xs font-medium text-slate-400">Cancelled</div>
      ) : (
        <div className="mt-2 flex gap-2">
          <button
            disabled={state === "working"}
            onClick={() => run(onConfirm, "confirmed")}
            className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            {state === "working" ? "Working…" : "Confirm"}
          </button>
          <button
            disabled={state === "working"}
            onClick={() => run(onCancel, "cancelled")}
            className="rounded-lg border border-slate-600 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-700/40 disabled:opacity-50"
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}
