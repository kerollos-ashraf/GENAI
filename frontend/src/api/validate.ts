/**
 * Runtime checks for backend responses. TypeScript types vanish at runtime, so data from the
 * network is verified before the UI relies on it; a malformed body becomes a clear ApiError
 * instead of a crash deep inside a component.
 */
import type { ChatResult, DocumentInfo, DocumentList, SyncReport, ToolCall } from "../types";
import { ApiError } from "./errors";

type Guard<T> = (value: unknown) => value is T;

const isRecord = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null && !Array.isArray(v);
const isString = (v: unknown): v is string => typeof v === "string";
const isNumber = (v: unknown): v is number => typeof v === "number";
const arrayOf =
  <T>(guard: Guard<T>): Guard<T[]> =>
  (v): v is T[] =>
    Array.isArray(v) && v.every(guard);

const isToolCall: Guard<ToolCall> = (v): v is ToolCall =>
  isRecord(v) && isString(v.name) && isRecord(v.args) && isString(v.status) && isString(v.output);

const isChatResult: Guard<ChatResult> = (v): v is ChatResult =>
  isRecord(v) &&
  isString(v.response) &&
  arrayOf(isString)(v.sources) &&
  arrayOf(isToolCall)(v.tool_calls);

const isDocumentInfo: Guard<DocumentInfo> = (v): v is DocumentInfo =>
  isRecord(v) &&
  isString(v.filename) &&
  isNumber(v.size_bytes) &&
  isNumber(v.chunks) &&
  typeof v.indexed === "boolean";

const isDocumentList: Guard<DocumentList> = (v): v is DocumentList =>
  isRecord(v) && arrayOf(isDocumentInfo)(v.documents) && isNumber(v.total_chunks);

const isSyncReport: Guard<SyncReport> = (v): v is SyncReport =>
  isRecord(v) &&
  (["added", "updated", "removed", "unchanged"] as const).every((k) => arrayOf(isString)(v[k])) &&
  isRecord(v.failed) &&
  Object.values(v.failed).every(isString);

const hasText: Guard<{ text: string }> = (v): v is { text: string } =>
  isRecord(v) && isString(v.text);

const hasStatus: Guard<{ status: string }> = (v): v is { status: string } =>
  isRecord(v) && isString(v.status);

function expect<T>(guard: Guard<T>, value: unknown): T {
  if (!guard(value)) throw new ApiError("Unexpected response from the backend");
  return value;
}

export const parse = {
  chat: (v: unknown) => expect(isChatResult, v),
  documents: (v: unknown) => expect(isDocumentList, v),
  sync: (v: unknown) => expect(isSyncReport, v),
  transcript: (v: unknown) => expect(hasText, v).text,
  health: (v: unknown) => expect(hasStatus, v).status,
};
