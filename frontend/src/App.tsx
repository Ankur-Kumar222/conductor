import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Send, Sparkles } from "lucide-react";
import { api, setUserId } from "./api";
import type { ChatSummary, Me, PendingConfirmation, StepResult, SyncStatus } from "./types";
import { Sidebar } from "./components/Sidebar";
import { StepBadges } from "./components/StepBadges";
import { PendingActionCard } from "./components/PendingActionCard";
import { Login } from "./components/Login";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

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
  const scrollRef = useRef<HTMLDivElement>(null);

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
    toast("Syncing your Workspace…", { description: "Indexing Gmail, Calendar & Drive." });
    try {
      await api.triggerSync();
      for (let i = 0; i < 12; i++) {
        await new Promise((r) => setTimeout(r, 2500));
        await refreshSync();
      }
      toast.success("Sync complete");
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
      toast.error("Couldn't open chat");
    }
  };

  const requestDeleteChat = (id: string) => {
    const title = chats.find((c) => c.id === id)?.title || "this chat";
    const short = title.length > 40 ? title.slice(0, 40) + "…" : title;
    toast("Delete chat?", {
      description: `"${short}" — this can't be undone.`,
      position: "top-center",
      action: { label: "Delete", onClick: () => doDeleteChat(id) },
      cancel: { label: "Cancel", onClick: () => {} },
    });
  };

  const doDeleteChat = async (id: string) => {
    try {
      await api.deleteChat(id);
      if (id === currentChatId) newChat();
      refreshChats();
      toast.success("Chat deleted");
    } catch {
      toast.error("Couldn't delete chat");
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
      toast.error("Query failed", { description: (e as Error).message });
      setTurns((t) => [...t, { role: "assistant", text: "Sorry — something went wrong with that request." }]);
    } finally {
      setBusy(false);
    }
  };

  const requestLogout = () => {
    toast("Log out?", {
      description: `You'll need to reconnect ${me?.email || "your account"} to continue.`,
      position: "top-center",
      action: { label: "Log out", onClick: () => doLogout() },
      cancel: { label: "Cancel", onClick: () => {} },
    });
  };

  const doLogout = async () => {
    await api.logout();
    setMe(null);
    setSync(null);
    setChats([]);
    setTurns([]);
    setCurrentChatId(null);
  };

  if (!authChecked) {
    return <div className="flex h-full items-center justify-center text-sm text-muted-foreground">Loading…</div>;
  }
  if (!me?.connected) {
    return <Login />;
  }

  const activeTitle = chats.find((c) => c.id === currentChatId)?.title || "New chat";

  return (
    <div className="flex h-full bg-background">
      <Sidebar
        me={me}
        sync={sync}
        syncing={syncing}
        onSync={doSync}
        onLogout={requestLogout}
        chats={chats}
        currentChatId={currentChatId}
        onNewChat={newChat}
        onSelectChat={selectChat}
        onDeleteChat={requestDeleteChat}
      />

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center border-b px-6">
          <div className="truncate text-sm font-medium">{activeTitle}</div>
        </header>

        <div ref={scrollRef} className="flex-1 overflow-y-auto">
          <div className="mx-auto flex max-w-3xl flex-col gap-6 px-6 py-8">
            {turns.length === 0 && (
              <div className="mt-14 flex flex-col items-center text-center">
                <div className="flex size-11 items-center justify-center rounded-2xl border bg-muted/40">
                  <Sparkles className="size-5 text-muted-foreground" />
                </div>
                <h2 className="mt-4 text-lg font-semibold tracking-tight">Ask across your Workspace</h2>
                <p className="mt-1.5 max-w-md text-sm text-muted-foreground">
                  Conductor classifies your intent, plans a multi-service execution graph, runs Gmail,
                  Calendar &amp; Drive in parallel, and synthesizes one answer.
                </p>
                <div className="mt-6 flex w-full max-w-md flex-col gap-2">
                  {SAMPLES.map((q) => (
                    <button
                      key={q}
                      onClick={() => send(q)}
                      className="rounded-xl border bg-background px-3.5 py-2.5 text-left text-[13px] text-foreground/80 transition-colors hover:border-foreground/25 hover:bg-accent/50"
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
                  <div className="max-w-[80%] rounded-3xl rounded-br-lg border bg-muted px-4 py-2.5 text-sm">
                    {turn.text}
                  </div>
                </div>
              ) : (
                <div key={i} className="flex flex-col">
                  <div className="whitespace-pre-wrap text-[14px] leading-relaxed text-foreground">
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
              ),
            )}

            {busy && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span className="inline-flex gap-1">
                  <Dot /> <Dot /> <Dot />
                </span>
                orchestrating…
              </div>
            )}
          </div>
        </div>

        <div className="px-6 pb-5">
          <div
            className={cn(
              "mx-auto flex max-w-3xl items-end gap-2 rounded-3xl border bg-background p-2 pl-4 shadow-sm transition-colors",
              "focus-within:border-foreground/30",
            )}
          >
            <Textarea
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
              className="max-h-40 min-h-[24px] flex-1 resize-none border-0 bg-transparent px-0 py-2 text-sm shadow-none focus-visible:ring-0 dark:bg-transparent"
            />
            <Button
              size="icon"
              onClick={() => send(input)}
              disabled={busy || !input.trim()}
              className="size-9 shrink-0 rounded-full"
            >
              <Send className="size-4" />
            </Button>
          </div>
          <div className="mx-auto mt-2 max-w-3xl text-center text-[11px] text-muted-foreground">
            Writes are drafted and always require your confirmation.
          </div>
        </div>
      </main>
    </div>
  );
}

function Dot() {
  return <span className="inline-block size-1.5 animate-pulse rounded-full bg-muted-foreground/60" />;
}
