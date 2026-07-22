import type { ChatDetail, ChatSummary, Me, QueryResponse, SyncStatus } from "./types";

const USER_KEY = "conductor_user_id";

export function getUserId(): string | null {
  return localStorage.getItem(USER_KEY);
}
export function setUserId(id: string) {
  localStorage.setItem(USER_KEY, id);
}
export function clearUserId() {
  localStorage.removeItem(USER_KEY);
}

function headers(): HeadersInit {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  const uid = getUserId();
  if (uid) h["X-User-Id"] = uid;
  return h;
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  loginUrl: "/api/v1/auth/google",

  async me(): Promise<Me> {
    return json<Me>(await fetch("/api/v1/auth/me", { headers: headers(), credentials: "include" }));
  },

  async logout(): Promise<void> {
    try {
      await fetch("/api/v1/auth/logout", {
        method: "POST",
        headers: headers(),
        credentials: "include",
      });
    } finally {
      clearUserId();
    }
  },

  async syncStatus(): Promise<SyncStatus> {
    return json<SyncStatus>(
      await fetch("/api/v1/sync/status", { headers: headers(), credentials: "include" }),
    );
  },

  async triggerSync(): Promise<unknown> {
    return json(
      await fetch("/api/v1/sync/trigger", {
        method: "POST",
        headers: headers(),
        credentials: "include",
        body: JSON.stringify({}),
      }),
    );
  },

  async query(q: string, chatId: string | null): Promise<QueryResponse> {
    return json<QueryResponse>(
      await fetch("/api/v1/query", {
        method: "POST",
        headers: headers(),
        credentials: "include",
        body: JSON.stringify({ query: q, chat_id: chatId }),
      }),
    );
  },

  async listChats(): Promise<ChatSummary[]> {
    return json<ChatSummary[]>(
      await fetch("/api/v1/chats", { headers: headers(), credentials: "include" }),
    );
  },

  async getChat(chatId: string): Promise<ChatDetail> {
    return json<ChatDetail>(
      await fetch(`/api/v1/chats/${chatId}`, { headers: headers(), credentials: "include" }),
    );
  },

  async deleteChat(chatId: string): Promise<void> {
    await fetch(`/api/v1/chats/${chatId}`, {
      method: "DELETE",
      headers: headers(),
      credentials: "include",
    });
  },

  async confirm(actionId: string): Promise<unknown> {
    return json(
      await fetch("/api/v1/actions/confirm", {
        method: "POST",
        headers: headers(),
        credentials: "include",
        body: JSON.stringify({ action_id: actionId }),
      }),
    );
  },

  async cancel(actionId: string): Promise<unknown> {
    return json(
      await fetch("/api/v1/actions/cancel", {
        method: "POST",
        headers: headers(),
        credentials: "include",
        body: JSON.stringify({ action_id: actionId }),
      }),
    );
  },
};
