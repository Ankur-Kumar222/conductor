import type { Me, QueryResponse, SyncStatus } from "./types";

const USER_KEY = "conductor_user_id";

export function getUserId(): string | null {
  return localStorage.getItem(USER_KEY);
}
export function setUserId(id: string) {
  localStorage.setItem(USER_KEY, id);
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

  async query(q: string, conversationId: string | null): Promise<QueryResponse> {
    return json<QueryResponse>(
      await fetch("/api/v1/query", {
        method: "POST",
        headers: headers(),
        credentials: "include",
        body: JSON.stringify({ query: q, conversation_id: conversationId }),
      }),
    );
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
