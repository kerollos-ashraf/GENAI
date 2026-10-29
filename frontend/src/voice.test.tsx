/** Voice in (recording -> transcription -> question) and voice out (the answer's player). */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ClientProvider } from "./api/ClientContext";
import { OmniCareClient } from "./api/client";
import App from "./App";
import { ANSWER, DOCUMENTS, fakeFetch, json, type Routes } from "./test/fakes";

/** Minimal MediaRecorder: emits one chunk of "audio" when stopped. */
class FakeMediaRecorder {
  static isTypeSupported = (type: string) => type.startsWith("audio/webm");
  mimeType = "audio/webm;codecs=opus";
  ondataavailable: ((e: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;
  constructor(readonly stream: { getTracks: () => { stop: () => void }[] }) {}
  start() {
    /* recording */
  }
  stop() {
    this.ondataavailable?.({ data: new Blob(["audio"], { type: this.mimeType }) });
    this.onstop?.();
  }
}

const track = { stop: vi.fn() };

beforeEach(() => {
  localStorage.clear();
  vi.stubGlobal("MediaRecorder", FakeMediaRecorder);
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: { getUserMedia: vi.fn(() => Promise.resolve({ getTracks: () => [track] })) },
  });
  URL.createObjectURL = vi.fn(() => "blob:recording");
  URL.revokeObjectURL = vi.fn();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function renderApp(routes: Routes) {
  const api = fakeFetch({
    "GET /api/v1/health": () => json({ status: "healthy" }),
    "GET /api/v1/documents": () => json(DOCUMENTS),
    ...routes,
  });
  render(
    <ClientProvider client={new OmniCareClient("", api.impl)}>
      <App />
    </ClientProvider>,
  );
  return api;
}

it("records, transcribes and asks; the recording stays playable", async () => {
  const api = renderApp({
    "POST /api/v1/transcribe": () => json({ text: "Are floods covered?" }),
    "POST /api/v1/chat": () => json(ANSWER),
  });
  await userEvent.click(screen.getByRole("button", { name: "Ask by voice" }));
  expect(await screen.findByText(/Listening… 0:00/)).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: "Send recording" }));
  const [question] = await screen.findAllByTestId("message");
  expect(question).toHaveTextContent("Spoken questionAre floods covered?");
  expect(screen.getByLabelText("Your recording")).toHaveAttribute("src", "blob:recording");
  expect(track.stop).toHaveBeenCalled(); // microphone released

  const audio = api.calls.find((c) => c.url === "/api/v1/transcribe")?.init.body as FormData;
  expect((audio.get("audio") as File).name).toBe("question.webm");
  await waitFor(() => {
    expect(screen.getAllByTestId("message")).toHaveLength(2);
  });
});

it("explains a failed transcription and adds nothing to the chat", async () => {
  renderApp({
    "POST /api/v1/transcribe": () => json({ detail: "No speech detected - please try again" }, 422),
  });
  await userEvent.click(screen.getByRole("button", { name: "Ask by voice" }));
  await userEvent.click(await screen.findByRole("button", { name: "Send recording" }));

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Backend error 422: No speech detected - please try again",
  );
  expect(screen.queryAllByTestId("message")).toHaveLength(0);
});

it("cancelling a recording sends nothing", async () => {
  const api = renderApp({});
  await userEvent.click(screen.getByRole("button", { name: "Ask by voice" }));
  await userEvent.click(await screen.findByRole("button", { name: "Cancel recording" }));
  expect(screen.getByTestId("composer-input")).toBeInTheDocument();
  expect(api.calls.some((c) => c.url === "/api/v1/transcribe")).toBe(false);
});

it("explains a blocked microphone", async () => {
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: { getUserMedia: () => Promise.reject(new DOMException("denied", "NotAllowedError")) },
  });
  renderApp({});
  await userEvent.click(screen.getByRole("button", { name: "Ask by voice" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(/Allow microphone access/);
});
