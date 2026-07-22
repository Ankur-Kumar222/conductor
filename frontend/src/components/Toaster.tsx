export interface ToastAction {
  label: string;
  onClick: () => void;
  tone?: "default" | "danger";
}

export interface Toast {
  id: number;
  message: string;
  tone?: "default" | "success" | "error";
  actions?: ToastAction[];
}

const TONE: Record<string, string> = {
  default: "border-slate-700 bg-[#1a2236] text-slate-100",
  success: "border-emerald-500/40 bg-emerald-500/10 text-emerald-200",
  error: "border-rose-500/40 bg-rose-500/10 text-rose-200",
};

const ACTION_TONE: Record<string, string> = {
  default: "border border-slate-600 text-slate-200 hover:bg-slate-700/50",
  danger: "bg-rose-600 text-white hover:bg-rose-500",
};

export function Toaster({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: number) => void }) {
  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((t) => {
        const hasActions = !!t.actions?.length;
        return (
          <div
            key={t.id}
            onClick={() => !hasActions && onDismiss(t.id)}
            className={`pointer-events-auto min-w-64 max-w-sm rounded-xl border px-4 py-3 text-sm shadow-lg ${
              hasActions ? "" : "cursor-pointer"
            } ${TONE[t.tone || "default"]}`}
          >
            <div>{t.message}</div>
            {hasActions && (
              <div className="mt-2.5 flex justify-end gap-2">
                {t.actions!.map((a) => (
                  <button
                    key={a.label}
                    onClick={() => {
                      a.onClick();
                      onDismiss(t.id);
                    }}
                    className={`rounded-lg px-3 py-1 text-xs font-semibold ${
                      ACTION_TONE[a.tone || "default"]
                    }`}
                  >
                    {a.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
