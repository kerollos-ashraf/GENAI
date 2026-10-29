/** Test doubles: a routing fake `fetch` that records requests, and canned backend payloads. */
type Handler = (init: RequestInit, url: string) => Response | Promise<Response>;
export type Routes = Partial<Record<string, Handler>>;

export interface RecordedCall {
  method: string;
  url: string;
  init: RequestInit;
}

export function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export function fakeFetch(routes: Routes) {
  const calls: RecordedCall[] = [];
  const impl: typeof fetch = async (input, init = {}) => {
    const url = input instanceof Request ? input.url : input.toString();
    const method = init.method ?? "GET";
    calls.push({ method, url, init });
    const handler = routes[`${method} ${url.split("?")[0] ?? url}`];
    if (!handler) return json({ detail: `no route for ${method} ${url}` }, 404);
    return handler(init, url);
  };
  return { impl, calls };
}

/** The JSON body a recorded request sent. */
export function sentJson(call: RecordedCall | undefined): Record<string, unknown> {
  if (typeof call?.init.body !== "string") throw new Error("request had no JSON body");
  return JSON.parse(call.init.body) as Record<string, unknown>;
}

/** A response that only arrives when the test says so (or fails if the request is aborted). */
export function deferred() {
  let release: (response: Response) => void = () => undefined;
  const handler: Handler = (init) =>
    new Promise<Response>((resolve, reject) => {
      release = resolve;
      init.signal?.addEventListener("abort", () => {
        reject(new DOMException("aborted", "AbortError"));
      });
    });
  return {
    handler,
    release: (response: Response) => {
      release(response);
    },
  };
}

export const WATER = "sample_policy.md § Section 1: Home Water Damage Coverage";

export const ANSWER = {
  response: `Covered up to **$25,000** [${WATER}].`,
  sources: [WATER],
  tool_calls: [
    { name: "search_policy", args: { query: "burst pipe" }, status: "success", output: "[...]" },
  ],
};

export const DOCUMENTS = {
  documents: [{ filename: "sample_policy.md", size_bytes: 411, chunks: 2, indexed: true }],
  total_chunks: 2,
};

export const SYNC = { added: [], updated: [], removed: [], unchanged: [], failed: {} };
