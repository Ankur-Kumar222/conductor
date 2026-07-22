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
  conversation_id: string;
  query: string;
  intent: Intent | null;
  response: string;
  actions_taken: ActionTaken[];
  steps: StepResult[];
  pending_confirmations: PendingConfirmation[];
  results: Record<string, unknown>;
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
