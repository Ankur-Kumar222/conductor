import { useEffect, useRef, useState } from "react";
import { api, setUserId } from "./api";
import type { ChatSummary, Me, PendingConfirmation, StepResult, SyncStatus } from "./types";
import { Sidebar } from "./components/Sidebar";
import { StepBadges } from "./components/StepBadges";
import { PendingActionCard } from "./components/PendingActionCard";
import { Login } from "./components/Login";
import { Toaster, type Toast } from "./components/Toaster";

interface Turn {
  role: "user" | "assistant";
  text: string;
  steps?: StepResult[];
  pending?: PendingConfirmation[];
}

const SAMPLES = [
  "Find emails from LinkedIn about jobs",
  "What's on my calendar next week where john@company.com is invited?",
  "Prepare for tomorrow's meeting with Acme Corp",
  "Show me PDFs in my Drive from this year",
  "Draft a reply to my most recent Wellfound email",
];

export default function App() {
  const [me, setMe] = useState<Me | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [sync, setSync] = useState<SyncStatus | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [chats, setChats] = useState<ChatSummary[]>([]);
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const toastId = useRef(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  const dismissToast = (id: number) => setToasts((ts) => ts.filter((t) => t.id !== id));
  const pushToast = (message: string, tone: Toast["tone"] = "default") => {
    const id = ++toastId.current;
    setToasts((ts) => [...ts, { id, message, tone }]);
    setTimeout(() => dismissToast(id), 3500);
  };
  const pushConfirm = (message: string, onConfirm: () => void) => {
    const id = ++toastId.current;
    setToasts((ts) => [
      ...ts,
      {
        id,
        message,
        actions: [
          { label: "Cancel", onClick: () => {}, tone: "default" },
          { label: "Delete", onClick: onConfirm, tone: "danger" },
        ],
      },
    ]);
  };

  useEffect(() => {
    api
      .me()
      .then((m) => {
        setMe(m);
        if (m.id) setUserId(m.id);
        api.syncStatus().then(setSync).catch(() => {});
        api.listChats().then(setChats).catch(() => {});
      })
      .catch(() => setMe(null))
      .finally(() => setAuthChecked(true));
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [turns, busy]);

  const refreshSync = () => api.syncStatus().then(setSync).catch(() => {});
  const refreshChats = () => api.listChats().then(setChats).catch(() => {});

  const doSync = async () => {
    setSyncing(true);
    try {
      await api.triggerSync();
      for (let i = 0; i < 12; i++) {
        await new Promise((r) => setTimeout(r, 2500));
        await refreshSync();
      }
    } finally {
      setSyncing(false);
    }
  };

  const newChat = () => {
    setCurrentChatId(null);
    setTurns([]);
    setInput("");
  };

  const selectChat = async (id: string) => {
    if (id === currentChatId) return;
    try {
      const chat = await api.getChat(id);
      setCurrentChatId(id);
      setTurns(
        chat.messages.map((m) => ({
          role: m.role,
          text: m.content,
          steps: m.meta?.steps,
          pending: m.meta?.pending_confirmations,
        })),
      );
    } catch {
      /* ignore */
    }
  };

  const requestDeleteChat = (id: string) => {
    const title = chats.find((c) => c.id === id)?.title || "this chat";
    const shortTitle = title.length > 34 ? title.slice(0, 34) + "…" : title;
    pushConfirm(`Delete "${shortTitle}"? This can't be undone.`, () => doDeleteChat(id));
  };

  const doDeleteChat = async (id: string) => {
    try {
      await api.deleteChat(id);
      if (id === currentChatId) newChat();
      refreshChats();
      pushToast("Chat deleted", "success");
    } catch {
      pushToast("Couldn't delete chat", "error");
    }
  };

  const send = async (q: string) => {
    const query = q.trim();
    if (!query || busy) return;
    setInput("");
    setTurns((t) => [...t, { role: "user", text: query }]);
    setBusy(true);
    try {
      const resp = await api.query(query, currentChatId);
      setCurrentChatId(resp.chat_id);
      setTurns((t) => [
        ...t,
        { role: "assistant", text: resp.response, steps: resp.steps, pending: resp.pending_confirmations },
      ]);
      refreshChats();
    } catch (e) {
      setTurns((t) => [...t, { role: "assistant", text: `Something went wrong: ${(e as Error).message}` }]);
    } finally {
      setBusy(false);
    }
  };

  const onLogout = async () => {
    await api.logout();
    setMe(null);
    setSync(null);
    setChats([]);
    setTurns([]);
    setCurrentChatId(null);
  };

  if (!authChecked) {
    return <div className="flex h-full items-center justify-center text-sm text-slate-500">Loading…</div>;
  }
  if (!me?.connected) {
    return <Login />;
  }

  return (
    <div className="flex h-full">
      <Toaster toasts={toasts} onDismiss={dismissToast} />
      <Sidebar
        me={me}
        sync={sync}
        syncing={syncing}
        onSync={doSync}
        onLogout={onLogout}
        chats={chats}
        currentChatId={currentChatId}
        onNewChat={newChat}
        onSelectChat={selectChat}
        onDeleteChat={requestDeleteChat}
      />

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-800/60 px-6 py-3">
          <div className="truncate text-sm font-medium text-slate-300">
            {chats.find((c) => c.id === currentChatId)?.title || "New chat"}
          </div>
          <div className="text-[11px] text-slate-500">GPT-5 · pgvector · Gmail / Calendar / Drive</div>
        </header>

        <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-6">
          <div className="mx-auto flex max-w-3xl flex-col gap-5">
            {turns.length === 0 && (
              <div className="mt-16 text-center text-slate-500">
                <div className="mb-2 text-2xl">🎼</div>
                <div className="text-lg font-medium text-slate-300">Ask across your Workspace</div>
                <p className="mx-auto mt-2 max-w-md text-sm">
                  Conductor classifies your intent, plans a multi-service execution graph, runs Gmail,
                  Calendar &amp; Drive in parallel, and synthesizes one answer.
                </p>
                <div className="mx-auto mt-6 flex max-w-md flex-col gap-2">
                  {SAMPLES.map((q) => (
                    <button
                      key={q}
                      onClick={() => send(q)}
                      className="rounded-lg border border-slate-800 bg-slate-900/30 px-3 py-2 text-left text-[13px] text-slate-300 hover:border-indigo-500/40 hover:bg-slate-800/40"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {turns.map((turn, i) =>
              turn.role === "user" ? (
                <div key={i} className="flex justify-end">
                  <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-indigo-600 px-4 py-2.5 text-sm text-white">
                    {turn.text}
                  </div>
                </div>
              ) : (
                <div key={i} className="flex justify-start">
                  <div className="w-full max-w-[92%] rounded-2xl rounded-bl-sm border border-slate-800 bg-[#141b2e] px-4 py-3">
                    <div className="whitespace-pre-wrap text-[14px] leading-relaxed text-slate-100">
                      {turn.text}
                    </div>
                    {turn.steps && turn.steps.length > 0 && <StepBadges steps={turn.steps} />}
                    {turn.pending?.map((pc) => (
                      <PendingActionCard
                        key={pc.action_id}
                        action={pc}
                        onConfirm={async (id) => {
                          await api.confirm(id);
                        }}
                        onCancel={async (id) => {
                          await api.cancel(id);
                        }}
                      />
                    ))}
                  </div>
                </div>
              ),
            )}

            {busy && (
              <div className="flex justify-start">
                <div className="rounded-2xl rounded-bl-sm border border-slate-800 bg-[#141b2e] px-4 py-3 text-sm text-slate-400">
                  <span className="inline-flex gap-1 align-middle">
                    <Dot /> <Dot /> <Dot />
                  </span>{" "}
                  orchestrating…
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="border-t border-slate-800/60 px-6 py-4">
          <div className="mx-auto flex max-w-3xl items-end gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send(input);
                }
              }}
              rows={1}
              placeholder="Ask across Gmail, Calendar & Drive…"
              disabled={busy}
              className="max-h-40 min-h-[44px] flex-1 resize-none rounded-xl border border-slate-700 bg-slate-900/60 px-4 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 focus:border-indigo-500 focus:outline-none disabled:opacity-50"
            />
            <button
              onClick={() => send(input)}
              disabled={busy || !input.trim()}
              className="h-[44px] rounded-xl bg-indigo-600 px-5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-40"
            >
              Send
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}

function Dot() {
  return <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-slate-500" />;
}
