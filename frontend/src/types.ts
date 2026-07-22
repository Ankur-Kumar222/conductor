export interface Entity {
  name: string;
  value: string;
}

export interface Intent {
  services: string[];
  intent: string;
  entities: Entity[];
  needs_clarification: boolean;
  clarification_question: string;
}

export interface StepResult {
  id: string;
  service: string;
  operation: string;
  description: string;
  status: string;
  result_count: number;
  error: string;
}

export interface ActionTaken {
  service: string;
  action: string;
  detail: string;
}

export interface PendingConfirmation {
  action_id: string;
  service: string;
  action_type: string;
  preview: string;
}

export interface QueryResponse {
  chat_id: string;
  message_id: string;
  query: string;
  intent: Intent | null;
  response: string;
  actions_taken: ActionTaken[];
  steps: StepResult[];
  pending_confirmations: PendingConfirmation[];
  results: Record<string, unknown>;
}

export interface ChatSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface MessageMeta {
  intent?: Intent | null;
  steps?: StepResult[];
  actions_taken?: ActionTaken[];
  pending_confirmations?: PendingConfirmation[];
}

export interface MessageOut {
  id: string;
  role: "user" | "assistant";
  content: string;
  meta: MessageMeta | null;
  created_at: string;
}

export interface ChatDetail {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: MessageOut[];
}

export interface Me {
  id: string;
  email: string | null;
  connected: boolean;
  scopes: string[];
}

export interface SyncStatus {
  user_id: string;
  services: Record<
    string,
    { last_synced_at: string | null; status: string; item_count: number; error: string | null }
  >;
}
