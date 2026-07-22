import { Plus, Trash2, RefreshCw, LogOut, MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
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
  const lastSync = sync?.services?.gmail?.last_synced_at ?? null;

  return (
    <aside className="flex w-72 shrink-0 flex-col border-r bg-sidebar">
      <div className="flex items-center gap-2.5 px-4 py-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-foreground text-background">
          <span className="text-sm font-semibold">C</span>
        </div>
        <div>
          <div className="text-sm font-semibold leading-none tracking-tight">Conductor</div>
          <div className="mt-1 text-[11px] text-muted-foreground">Workspace Orchestrator</div>
        </div>
      </div>

      <div className="px-3">
        <Button onClick={onNewChat} className="w-full justify-start gap-2 rounded-xl">
          <Plus className="size-4" /> New chat
        </Button>
      </div>

      <div className="px-4 pb-1 pt-4 text-[11px] font-medium uppercase tracking-wide text-muted-foreground/70">
        Chats
      </div>
      <ScrollArea className="min-h-0 flex-1 px-2">
        {chats.length === 0 && (
          <div className="px-2 py-2 text-xs text-muted-foreground">No chats yet.</div>
        )}
        <div className="flex flex-col gap-0.5 pb-2">
          {chats.map((c) => {
            const active = c.id === currentChatId;
            return (
              <div
                key={c.id}
                onClick={() => onSelectChat(c.id)}
                className={cn(
                  "group flex cursor-pointer items-center gap-2 rounded-lg px-2.5 py-2 text-[13px] transition-colors",
                  active
                    ? "bg-accent text-accent-foreground"
                    : "text-foreground/80 hover:bg-accent/60",
                )}
              >
                <MessageSquare className="size-3.5 shrink-0 text-muted-foreground" />
                <span className="min-w-0 flex-1 truncate">{c.title}</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteChat(c.id);
                  }}
                  className="shrink-0 rounded p-0.5 text-muted-foreground opacity-0 transition hover:text-destructive group-hover:opacity-100"
                  title="Delete chat"
                >
                  <Trash2 className="size-3.5" />
                </button>
              </div>
            );
          })}
        </div>
      </ScrollArea>

      <Separator />

      <div className="px-4 py-3">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground/70">
            Index
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={onSync}
            disabled={syncing}
            className="h-6 gap-1.5 px-2 text-[11px]"
          >
            <RefreshCw className={cn("size-3", syncing && "animate-spin")} />
            {syncing ? "Syncing" : "Sync"}
          </Button>
        </div>
        <div className="flex gap-1.5">
          {services.map((s) => {
            const st = sync?.services?.[s.key];
            return (
              <div key={s.key} className="flex-1 rounded-lg border bg-background px-2 py-1.5 text-center">
                <div className="text-[11px] text-muted-foreground">{s.label}</div>
                <div className="text-xs font-medium tabular-nums">{st ? st.item_count : "—"}</div>
              </div>
            );
          })}
        </div>
        {lastSync && (
          <div className="mt-1.5 text-center text-[10px] text-muted-foreground">
            synced {timeAgo(lastSync)}
          </div>
        )}
      </div>

      <Separator />

      <div className="flex items-center justify-between gap-2 px-4 py-3">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-muted-foreground">
            <span className="inline-block size-1.5 rounded-full bg-foreground" /> Connected
          </div>
          <div className="mt-0.5 truncate text-[13px]">{me?.email}</div>
        </div>
        <Button variant="ghost" size="icon" onClick={onLogout} title="Log out" className="shrink-0">
          <LogOut className="size-4" />
        </Button>
      </div>
    </aside>
  );
}
