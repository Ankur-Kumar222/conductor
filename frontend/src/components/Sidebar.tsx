import type { ChatSummary, Me, SyncStatus } from "../types";

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
  onLogout,
  chats,
  currentChatId,
  onNewChat,
  onSelectChat,
  onDeleteChat,
}: {
  me: Me | null;
  sync: SyncStatus | null;
  syncing: boolean;
  onSync: () => void;
  onLogout: () => void;
  chats: ChatSummary[];
  currentChatId: string | null;
  onNewChat: () => void;
  onSelectChat: (id: string) => void;
  onDeleteChat: (id: string) => void;
}) {
  const services = [
    { key: "gmail", label: "Gmail" },
    { key: "gcal", label: "Calendar" },
    { key: "drive", label: "Drive" },
  ];

  return (
    <aside className="flex w-72 shrink-0 flex-col border-r border-slate-800/60 bg-[#0f1424]">
      <div className="flex items-center gap-2 px-5 pt-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 text-sm font-bold">
          C
        </div>
        <div>
          <div className="text-[15px] font-semibold leading-none">Conductor</div>
          <div className="mt-0.5 text-[11px] text-slate-500">Workspace Orchestrator</div>
        </div>
      </div>

      <div className="px-5 pt-4">
        <button
          onClick={onNewChat}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-500"
        >
          <span className="text-base leading-none">＋</span> New chat
        </button>
      </div>

      {/* chat list */}
      <div className="mt-4 min-h-0 flex-1 overflow-y-auto px-3">
        <div className="px-2 pb-1 text-[11px] uppercase tracking-wide text-slate-500">Chats</div>
        {chats.length === 0 && (
          <div className="px-2 py-2 text-xs text-slate-600">No chats yet.</div>
        )}
        {chats.map((c) => {
          const active = c.id === currentChatId;
          return (
            <div
              key={c.id}
              onClick={() => onSelectChat(c.id)}
              className={`group flex cursor-pointer items-center justify-between gap-2 rounded-lg px-2.5 py-2 text-[13px] ${
                active ? "bg-slate-800 text-slate-100" : "text-slate-300 hover:bg-slate-800/50"
              }`}
            >
              <span className="min-w-0 flex-1 truncate">{c.title}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteChat(c.id);
                }}
                className="shrink-0 rounded px-1 text-slate-500 opacity-0 hover:text-rose-400 group-hover:opacity-100"
                title="Delete chat"
              >
                ✕
              </button>
            </div>
          );
        })}
      </div>

      {/* index status */}
      <div className="border-t border-slate-800/60 px-5 py-3">
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
        <div className="flex gap-2">
          {services.map((s) => {
            const st = sync?.services?.[s.key];
            return (
              <div key={s.key} className="flex-1 rounded-lg bg-slate-900/40 px-2 py-1.5 text-center">
                <div className="text-[11px] text-slate-400">{s.label}</div>
                <div className="text-[11px] text-slate-500">{st ? st.item_count : "—"}</div>
              </div>
            );
          })}
        </div>
        {sync?.services?.gmail?.last_synced_at && (
          <div className="mt-1 text-center text-[10px] text-slate-600">
            synced {timeAgo(sync.services.gmail.last_synced_at)}
          </div>
        )}
      </div>

      {/* account */}
      <div className="border-t border-slate-800/60 px-5 py-3">
        <div className="flex items-center justify-between gap-2">
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-slate-500">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" /> Connected
            </div>
            <div className="mt-0.5 truncate text-[13px] text-slate-200">{me?.email}</div>
          </div>
          <button
            onClick={onLogout}
            className="shrink-0 rounded-lg border border-slate-700 px-2.5 py-1 text-[11px] font-medium text-slate-300 hover:border-rose-500/40 hover:bg-rose-500/10 hover:text-rose-300"
          >
            Log out
          </button>
        </div>
      </div>
    </aside>
  );
}
