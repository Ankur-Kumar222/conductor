import type { Me, SyncStatus } from "../types";
import { api } from "../api";

const SAMPLES = [
  "Find emails from LinkedIn about jobs",
  "Show me spreadsheets in my Drive",
  "What's on my calendar next week?",
  "Find emails and documents about my job interviews",
  "Draft a reply to my most recent Wellfound email",
];

function timeAgo(iso: string | null): string {
  if (!iso) return "never";
  const d = (Date.now() - new Date(iso).getTime()) / 1000;
  if (d < 60) return "just now";
  if (d < 3600) return `${Math.floor(d / 60)}m ago`;
  if (d < 86400) return `${Math.floor(d / 3600)}h ago`;
  return `${Math.floor(d / 86400)}d ago`;
}

export function Sidebar({
  me,
  sync,
  syncing,
  onSync,
  onSample,
}: {
  me: Me | null;
  sync: SyncStatus | null;
  syncing: boolean;
  onSync: () => void;
  onSample: (q: string) => void;
}) {
  const connected = me?.connected;
  const services = [
    { key: "gmail", label: "Gmail" },
    { key: "gcal", label: "Calendar" },
    { key: "drive", label: "Drive" },
  ];

  return (
    <aside className="flex w-72 shrink-0 flex-col gap-5 border-r border-slate-800/60 bg-[#0f1424] p-5">
      <div>
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 text-sm font-bold">
            C
          </div>
          <div>
            <div className="text-[15px] font-semibold leading-none">Conductor</div>
            <div className="mt-0.5 text-[11px] text-slate-500">Workspace Orchestrator</div>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-3">
        {connected ? (
          <>
            <div className="text-[11px] uppercase tracking-wide text-slate-500">Connected</div>
            <div className="mt-1 truncate text-sm text-slate-200">{me?.email}</div>
          </>
        ) : (
          <>
            <div className="text-sm text-slate-300">Not connected</div>
            <a
              href={api.loginUrl}
              className="mt-2 block rounded-lg bg-indigo-600 px-3 py-1.5 text-center text-xs font-semibold text-white hover:bg-indigo-500"
            >
              Connect Google
            </a>
          </>
        )}
      </div>

      {connected && (
        <div>
          <div className="mb-2 flex items-center justify-between">
            <span className="text-[11px] uppercase tracking-wide text-slate-500">Index</span>
            <button
              onClick={onSync}
              disabled={syncing}
              className="rounded-md border border-slate-700 px-2 py-0.5 text-[11px] font-medium text-slate-300 hover:bg-slate-800 disabled:opacity-50"
            >
              {syncing ? "Syncing…" : "Sync now"}
            </button>
          </div>
          <div className="space-y-1.5">
            {services.map((s) => {
              const st = sync?.services?.[s.key];
              return (
                <div
                  key={s.key}
                  className="flex items-center justify-between rounded-lg bg-slate-900/40 px-2.5 py-1.5 text-xs"
                >
                  <span className="text-slate-300">{s.label}</span>
                  <span className="text-slate-500">
                    {st ? `${st.item_count} · ${timeAgo(st.last_synced_at)}` : "—"}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div>
        <div className="mb-2 text-[11px] uppercase tracking-wide text-slate-500">Try asking</div>
        <div className="space-y-1.5">
          {SAMPLES.map((q) => (
            <button
              key={q}
              onClick={() => onSample(q)}
              className="block w-full rounded-lg border border-slate-800 bg-slate-900/30 px-3 py-2 text-left text-[12.5px] text-slate-300 hover:border-indigo-500/40 hover:bg-slate-800/40"
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-auto text-[10px] leading-relaxed text-slate-600">
        Writes are drafted &amp; require confirmation. Nothing is sent or changed automatically.
      </div>
    </aside>
  );
}
