/** Shapes of the FastAPI contract (backend/app/api/schemas.py) and of the UI's own state. */

export interface ToolCall {
  name: string;
  args: Record<string, unknown>;
  status: string; // "success" | "error"
  output: string;
}

export interface ChatResult {
  response: string;
  sources: string[];
  tool_calls: ToolCall[];
}

export interface DocumentInfo {
  filename: string;
  size_bytes: number;
  chunks: number;
  indexed: boolean;
}

export interface DocumentList {
  documents: DocumentInfo[];
  total_chunks: number;
}

export interface SyncReport {
  added: string[];
  updated: string[];
  removed: string[];
  unchanged: string[];
  failed: Record<string, string>;
}

export type Role = "user" | "assistant";

export interface Message {
  id: string;
  role: Role;
  content: string;
  sources: string[];
  toolCalls: ToolCall[];
  /** User: the question was spoken. */
  voice?: boolean;
  /** User: object URL of their own recording, so it stays playable in the chat. */
  audioUrl?: string;
  /** Assistant: the question this answers, so a failed answer can be retried. */
  question?: string;
  /** Assistant: the answer failed; `content` explains why. */
  error?: boolean;
}

export type ReplyMode = "auto" | "always" | "off";

export type Theme = "system" | "light" | "dark";
