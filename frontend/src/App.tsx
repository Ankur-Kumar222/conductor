import { useEffect, useRef, useState } from "react";
import { api, setUserId } from "./api";
import type { Me, QueryResponse, SyncStatus } from "./types";
import { Sidebar } from "./components/Sidebar";
import { StepBadges } from "./components/StepBadges";
import { PendingActionCard } from "./components/PendingActionCard";
import { Login } from "./components/Login";

interface Turn {
  role: "user" | "assistant";
  text: string;
  response?: QueryResponse;
}

export default function App() {
  const [me, setMe] = useState<Me | null>(null);
  const [sync, setSync] = useState<SyncStatus | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api
      .me()
      .then((m) => {
        setMe(m);
        if (m.id) setUserId(m.id);
        api.syncStatus().then(setSync).catch(() => {});
      })
      .catch(() => setMe(null))
      .finally(() => setAuthChecked(true));
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [turns, busy]);

  const refreshSync = () => api.syncStatus().then(setSync).catch(() => {});

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

  const send = async (q: string) => {
    const query = q.trim();
    if (!query || busy) return;
    setInput("");
    setTurns((t) => [...t, { role: "user", text: query }]);
    setBusy(true);
    try {
      const resp = await api.query(query, conversationId);
      setConversationId(resp.conversation_id);
      setTurns((t) => [...t, { role: "assistant", text: resp.response, response: resp }]);
    } catch (e) {
      setTurns((t) => [
        ...t,
        { role: "assistant", text: `Something went wrong: ${(e as Error).message}` },
      ]);
    } finally {
      setBusy(false);
    }
  };

  const onLogout = async () => {
    await api.logout();
    setMe(null);
    setSync(null);
    setTurns([]);
    setConversationId(null);
  };

  const onConfirm = async (id: string) => {
    await api.confirm(id);
  };
  const onCancel = async (id: string) => {
    await api.cancel(id);
  };

  if (!authChecked) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-slate-500">Loading…</div>
    );
  }

  if (!me?.connected) {
    return <Login />;
  }

  return (
    <div className="flex h-full">
      <Sidebar
        me={me}
        sync={sync}
        syncing={syncing}
        onSync={doSync}
        onSample={send}
        onLogout={onLogout}
      />

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-800/60 px-6 py-3">
          <div className="text-sm font-medium text-slate-300">Orchestrator</div>
          <div className="text-[11px] text-slate-500">
            {me?.connected ? "GPT-5 · pgvector · Gmail / Calendar / Drive" : "Connect Google to begin"}
          </div>
        </header>

        <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-6">
          <div className="mx-auto flex max-w-3xl flex-col gap-5">
            {turns.length === 0 && (
              <div className="mt-20 text-center text-slate-500">
                <div className="mb-2 text-2xl">🎼</div>
                <div className="text-lg font-medium text-slate-300">Ask across your Workspace</div>
                <p className="mx-auto mt-2 max-w-md text-sm">
                  Conductor classifies your intent, plans a multi-service execution graph, runs Gmail,
                  Calendar &amp; Drive in parallel, and synthesizes one answer.
                </p>
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
                    {turn.response && <StepBadges steps={turn.response.steps} />}
                    {turn.response?.pending_confirmations.map((pc) => (
                      <PendingActionCard
                        key={pc.action_id}
                        action={pc}
                        onConfirm={onConfirm}
                        onCancel={onCancel}
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
              placeholder={me?.connected ? "Ask across Gmail, Calendar & Drive…" : "Connect Google first"}
              disabled={!me?.connected || busy}
              className="max-h-40 min-h-[44px] flex-1 resize-none rounded-xl border border-slate-700 bg-slate-900/60 px-4 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 focus:border-indigo-500 focus:outline-none disabled:opacity-50"
            />
            <button
              onClick={() => send(input)}
              disabled={!me?.connected || busy || !input.trim()}
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
