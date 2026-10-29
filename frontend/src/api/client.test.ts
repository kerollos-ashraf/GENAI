import { ANSWER, SYNC, deferred, fakeFetch, json, sentJson } from "../test/fakes";
import { ApiError, CancelledError, OmniCareClient, describeError } from "./client";

describe("OmniCareClient", () => {
  it("sends the assessment's chat contract and returns the validated answer", async () => {
    const api = fakeFetch({ "POST /api/v1/chat": () => json(ANSWER) });
    const client = new OmniCareClient("", api.impl);

    await expect(client.chat("usr_123", "Is a burst pipe covered?", "s1")).resolves.toEqual(ANSWER);
    expect(sentJson(api.calls[0])).toEqual({
      user_id: "usr_123",
      message: "Is a burst pipe covered?",
      session_id: "s1",
    });
  });

  it("rejects a malformed response instead of passing it to the UI", async () => {
    const api = fakeFetch({ "POST /api/v1/chat": () => json({ response: 42 }) });
    await expect(new OmniCareClient("", api.impl).chat("u", "hi", "s")).rejects.toThrow(
      "Unexpected response from the backend",
    );
  });

  it("reports the backend's detail message", async () => {
    const api = fakeFetch({
      "POST /api/v1/chat": () =>
        json({ detail: "The AI provider rejected the request (HTTP 429)" }, 502),
    });
    await expect(new OmniCareClient("", api.impl).chat("u", "hi", "s")).rejects.toThrow(
      "Backend error 502: The AI provider rejected the request (HTTP 429)",
    );
  });

  it("reports validation errors readably", () => {
    expect(describeError(422, { detail: [{ msg: "String should match pattern" }] }, "")).toBe(
      "Backend error 422: String should match pattern",
    );
  });

  it("explains a proxy that cannot reach the backend", () => {
    expect(describeError(502, undefined, "<html>Bad Gateway</html>")).toBe(
      "Could not reach the backend (HTTP 502)",
    );
  });

  it("turns network failures into ApiError", async () => {
    const failing: typeof fetch = () => Promise.reject(new TypeError("Failed to fetch"));
    const error: unknown = await new OmniCareClient("", failing)
      .listDocuments()
      .catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).message).toBe(
      "Could not reach the backend: TypeError: Failed to fetch",
    );
  });

  it("cancels on request, with a CancelledError rather than an error to show", async () => {
    const slow = deferred();
    const api = fakeFetch({ "POST /api/v1/chat": slow.handler });
    const controller = new AbortController();
    const pending = new OmniCareClient("", api.impl).chat("u", "hi", "s", controller.signal);
    controller.abort();
    await expect(pending).rejects.toBeInstanceOf(CancelledError);
  });

  it("is unhealthy instead of throwing when the backend is down", async () => {
    const api = fakeFetch({});
    await expect(new OmniCareClient("", api.impl).isHealthy()).resolves.toBe(false);
  });

  it("URL-encodes filenames when deleting", async () => {
    const api = fakeFetch({ "DELETE /api/v1/documents/my%20notes.pdf": () => json(SYNC) });
    await new OmniCareClient("", api.impl).deleteDocument("my notes.pdf");
    expect(api.calls[0]).toMatchObject({
      method: "DELETE",
      url: "/api/v1/documents/my%20notes.pdf",
    });
  });

  it("uploads documents and audio as multipart form fields", async () => {
    const api = fakeFetch({
      "POST /api/v1/documents": () => json({ ...SYNC, added: ["a.md"] }),
      "POST /api/v1/transcribe": () => json({ text: "Are floods covered?" }),
    });
    const client = new OmniCareClient("", api.impl);
    await client.uploadDocument(new Blob(["# A"]), "a.md");
    await expect(client.transcribe(new Blob(["x"]), "question.webm")).resolves.toBe(
      "Are floods covered?",
    );

    const doc = api.calls[0]?.init.body as FormData;
    const audio = api.calls[1]?.init.body as FormData;
    expect((doc.get("file") as File).name).toBe("a.md");
    expect((audio.get("audio") as File).name).toBe("question.webm");
  });
});
