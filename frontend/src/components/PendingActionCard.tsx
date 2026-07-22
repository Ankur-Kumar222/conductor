import { useState } from "react";
import { ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
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
    <div className="mt-3 rounded-xl border bg-muted/30 p-3">
      <div className="mb-2 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <ShieldAlert className="size-3.5" />
        Needs confirmation · {ACTION_LABEL[action.action_type] || action.action_type}
      </div>
      <pre className="max-h-56 overflow-auto whitespace-pre-wrap break-words rounded-lg border bg-background p-3 font-sans text-[12.5px] leading-relaxed text-foreground/90">
        {action.preview}
      </pre>
      {state === "confirmed" ? (
        <div className="mt-2 text-xs font-medium text-foreground">✓ Done</div>
      ) : state === "cancelled" ? (
        <div className="mt-2 text-xs text-muted-foreground">Cancelled</div>
      ) : (
        <div className="mt-2.5 flex gap-2">
          <Button size="sm" disabled={state === "working"} onClick={() => run(onConfirm, "confirmed")}>
            {state === "working" ? "Working…" : "Confirm"}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            disabled={state === "working"}
            onClick={() => run(onCancel, "cancelled")}
          >
            Cancel
          </Button>
        </div>
      )}
    </div>
  );
}
