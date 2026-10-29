/**
 * Typed gateway to the OmniCare backend. UI code never calls `fetch` directly: every call either
 * returns validated data or throws an `ApiError` whose message is safe to show. Requests go to
 * the page's own origin under `/api`; nginx (Docker) or Vite (dev) proxies them to FastAPI.
 */
import type { ChatResult, DocumentList, SyncReport } from "../types";
import { ApiError, CancelledError } from "./errors";
import { parse } from "./validate";

export { ApiError, CancelledError } from "./errors";

const TIMEOUT = { default: 30_000, chat: 90_000, upload: 300_000, health: 3_000, list: 10_000 };
const GATEWAY_ERRORS = new Set([500, 502, 503, 504]);

interface RequestOptions {
  json?: unknown;
  form?: FormData;
  timeout?: number;
  /** Lets the caller cancel (e.g. "New conversation"); throws CancelledError. */
  signal?: AbortSignal;
}

export class OmniCareClient {
  private readonly fetchImpl: typeof fetch;

  constructor(
    private readonly baseUrl = "",
    fetchImpl?: typeof fetch,
  ) {
    this.fetchImpl = fetchImpl ?? ((input, init) => fetch(input, init));
  }

  async isHealthy(): Promise<boolean> {
    try {
      const body = await this.request("GET", "/api/v1/health", { timeout: TIMEOUT.health });
      return parse.health(body) === "healthy";
    } catch {
      return false;
    }
  }

  async chat(
    userId: string,
    message: string,
    sessionId: string,
    signal?: AbortSignal,
  ): Promise<ChatResult> {
    const body = await this.request("POST", "/api/v1/chat", {
      json: { user_id: userId, message, session_id: sessionId },
      timeout: TIMEOUT.chat,
      signal,
    });
    return parse.chat(body);
  }

  async transcribe(audio: Blob, filename = "question.webm", signal?: AbortSignal): Promise<string> {
    const form = new FormData();
    form.append("audio", audio, filename);
    const body = await this.request("POST", "/api/v1/transcribe", {
      form,
      timeout: TIMEOUT.chat,
      signal,
    });
    return parse.transcript(body);
  }

  async listDocuments(): Promise<DocumentList> {
    return parse.documents(
      await this.request("GET", "/api/v1/documents", { timeout: TIMEOUT.list }),
    );
  }

  async uploadDocument(file: Blob, filename: string): Promise<SyncReport> {
    const form = new FormData();
    form.append("file", file, filename);
    const body = await this.request("POST", "/api/v1/documents", { form, timeout: TIMEOUT.upload });
    return parse.sync(body);
  }

  async deleteDocument(filename: string): Promise<SyncReport> {
    const path = `/api/v1/documents/${encodeURIComponent(filename)}`;
    return parse.sync(await this.request("DELETE", path));
  }

  async reindex(): Promise<SyncReport> {
    const body = await this.request("POST", "/api/v1/documents/reindex", {
      timeout: TIMEOUT.upload,
    });
    return parse.sync(body);
  }

  // -- transport ----------------------------------------------------------------------------

  private async request(method: string, path: string, options: RequestOptions = {}) {
    const timeout = AbortSignal.timeout(options.timeout ?? TIMEOUT.default);
    const signal = options.signal ? AbortSignal.any([options.signal, timeout]) : timeout;
    const init: RequestInit = { method, signal };
    if (options.json !== undefined) {
      init.headers = { "Content-Type": "application/json" };
      init.body = JSON.stringify(options.json);
    } else if (options.form) {
      init.body = options.form;
    }

    let response: Response;
    try {
      response = await this.fetchImpl(this.baseUrl + path, init);
    } catch (error) {
      if (options.signal?.aborted) throw new CancelledError();
      const reason = timeout.aborted ? "the request timed out" : String(error);
      throw new ApiError(`Could not reach the backend: ${reason}`);
    }

    const text = await response.text();
    const body = parseJson(text);
    if (!response.ok) {
      throw new ApiError(describeError(response.status, body, text), response.status);
    }
    return body;
  }
}

function parseJson(text: string): unknown {
  try {
    return text ? (JSON.parse(text) as unknown) : null;
  } catch {
    return undefined;
  }
}

/** FastAPI errors carry `detail` (a string, or a list of validation errors). A gateway error
 * without one means the proxy could not reach the backend at all. */
export function describeError(status: number, body: unknown, text: string): string {
  const detail =
    typeof body === "object" && body !== null ? (body as { detail?: unknown }).detail : undefined;
  if (typeof detail === "string") return `Backend error ${status}: ${detail}`;
  if (Array.isArray(detail)) {
    const reasons = detail
      .map((d: unknown) =>
        typeof d === "object" && d !== null && "msg" in d ? String(d.msg) : JSON.stringify(d),
      )
      .join("; ");
    return `Backend error ${status}: ${reasons}`;
  }
  if (GATEWAY_ERRORS.has(status)) return `Could not reach the backend (HTTP ${status})`;
  return `Backend error ${status}: ${text.slice(0, 200) || "no details"}`;
}
