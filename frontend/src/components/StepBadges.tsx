import { Check, X, Minus, Clock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { StepResult } from "../types";

const SERVICE_LABEL: Record<string, string> = { gmail: "Gmail", gcal: "Calendar", drive: "Drive" };

const STATUS = {
  ok: { icon: Check, cls: "text-foreground" },
  error: { icon: X, cls: "text-destructive" },
  skipped: { icon: Minus, cls: "text-muted-foreground" },
  pending_confirmation: { icon: Clock, cls: "text-foreground" },
} as const;

export function StepBadges({ steps }: { steps: StepResult[] }) {
  if (!steps.length) return null;
  return (
    <div className="mt-3 flex flex-wrap gap-1.5">
      {steps.map((s) => {
        const st = STATUS[s.status as keyof typeof STATUS] ?? STATUS.skipped;
        const Icon = st.icon;
        return (
          <Badge
            key={s.id}
            variant="secondary"
            title={s.error || s.description}
            className="gap-1 font-normal text-muted-foreground"
          >
            <Icon className={cn("size-3", st.cls)} />
            <span className="text-foreground/80">{SERVICE_LABEL[s.service] || s.service}</span>
            <span className="opacity-40">·</span>
            <span>{s.operation}</span>
            {s.result_count > 0 && <span className="opacity-50">· {s.result_count}</span>}
          </Badge>
        );
      })}
    </div>
  );
}
