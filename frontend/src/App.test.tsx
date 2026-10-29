import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ClientProvider } from "./api/ClientContext";
import { OmniCareClient } from "./api/client";
import App from "./App";
import {
  ANSWER,
  DOCUMENTS,
  SYNC,
  deferred,
  fakeFetch,
  json,
  sentJson,
  type Routes,
} from "./test/fakes";

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
  const chatCalls = () => api.calls.filter((c) => c.url === "/api/v1/chat");
  return { api, chatCalls };
}

async function ask(question: string) {
  await userEvent.type(screen.getByTestId("composer-input"), `${question}{Enter}`);
}

beforeEach(() => {
  localStorage.clear();
  delete document.documentElement.dataset.theme;
});

it("asks a suggestion and shows the cited answer, then starts over", async () => {
  const { chatCalls } = renderApp({ "POST /api/v1/chat": () => json(ANSWER) });
  expect(await screen.findByText("Online")).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: /Is a burst pipe covered\?/ }));
  const [question, reply] = await screen.findAllByTestId("message");
  expect(question).toHaveTextContent("Is water damage from a burst pipe covered?");
  expect(reply).toHaveTextContent("Covered up to $25,000¹.");
  expect(within(reply).getByLabelText("Sources")).toHaveTextContent(
    "Section 1: Home Water Damage Coverage",
  );
  expect(sentJson(chatCalls()[0]).user_id).toBe("usr_123");

  await userEvent.click(screen.getByRole("button", { name: "New conversation" }));
  expect(screen.queryAllByTestId("message")).toHaveLength(0);
  expect(screen.getByText("How can we help with your policy?")).toBeInTheDocument();
});

it("keeps one conversation id per conversation and a new one after reset", async () => {
  const { chatCalls } = renderApp({ "POST /api/v1/chat": () => json(ANSWER) });
  await ask("one");
  await screen.findAllByTestId("message");
  await ask("two");
  await screen.findByText("two");
  await userEvent.click(screen.getByRole("button", { name: "New conversation" }));
  await ask("three");
  await screen.findByText("three");

  const sessions = chatCalls().map((c) => sentJson(c).session_id);
  expect(sessions[0]).toBe(sessions[1]);
  expect(sessions[2]).not.toBe(sessions[0]);
});

it("shows a failed answer with a working Try again", async () => {
  let attempt = 0;
  const { chatCalls } = renderApp({
    "POST /api/v1/chat": () =>
      ++attempt === 1 ? json({ detail: "GROQ_API_KEY is not set." }, 503) : json(ANSWER),
  });
  await ask("Is a burst pipe covered?");
  expect(await screen.findByText(/Backend error 503: GROQ_API_KEY is not set\./)).toBeVisible();

  await userEvent.click(screen.getByRole("button", { name: "Try again" }));
  expect(await screen.findByText(/Covered up to/)).toBeInTheDocument();
  expect(screen.queryByText(/GROQ_API_KEY/)).toBeNull(); // the failure was replaced
  expect(screen.getAllByTestId("message")).toHaveLength(2); // question not duplicated
  expect(sentJson(chatCalls()[1]).message).toBe("Is a burst pipe covered?");
});

it("stops an answer in flight; the question stays and nothing else is added", async () => {
  const slow = deferred();
  renderApp({ "POST /api/v1/chat": slow.handler });
  await ask("Are floods covered?");
  const stop = await screen.findByRole("button", { name: "Stop" });

  await userEvent.click(stop);
  await waitFor(() => {
    expect(screen.queryByTestId("thinking")).toBeNull();
  });
  expect(screen.getAllByTestId("message")).toHaveLength(1);
  expect(screen.getByTestId("composer-input")).toBeEnabled();
});

it("copies an answer without its citation markers", async () => {
  const user = userEvent.setup();
  renderApp({ "POST /api/v1/chat": () => json(ANSWER) });
  await user.type(screen.getByTestId("composer-input"), "q{Enter}");
  await user.click(await screen.findByRole("button", { name: "Copy answer" }));

  expect(await navigator.clipboard.readText()).toBe("Covered up to $25,000.");
  expect(screen.getByRole("button", { name: "Copied" })).toBeInTheDocument();
});

it("shows the offline state when the backend is down", async () => {
  renderApp({
    "GET /api/v1/health": () => json({}, 502),
    "GET /api/v1/documents": () => json({}, 502),
  });
  expect(await screen.findByText("Can't reach the service")).toBeInTheDocument();
});

it("switches and remembers the theme", async () => {
  renderApp({});
  await userEvent.click(screen.getByRole("radio", { name: /Dark/ }));
  expect(document.documentElement.dataset.theme).toBe("dark");
  expect(localStorage.getItem("omnicare_theme")).toBe("dark");

  await userEvent.click(screen.getByRole("radio", { name: /System/ }));
  expect(document.documentElement.dataset.theme).toBeUndefined();
});

it("lists, uploads and deletes knowledge-base documents", async () => {
  const { api } = renderApp({
    "POST /api/v1/documents": () => json({ ...SYNC, added: ["pets.md"] }, 201),
    "DELETE /api/v1/documents/sample_policy.md": () =>
      json({ ...SYNC, removed: ["sample_policy.md"] }),
  });
  await userEvent.click(screen.getByText("Knowledge base"));
  expect(await screen.findByText("sample_policy.md")).toBeInTheDocument();
  expect(screen.getByText("1 document, 2 passages searchable")).toBeInTheDocument();

  await userEvent.upload(screen.getByTestId("document-input"), new File(["# Pets"], "pets.md"));
  await userEvent.click(screen.getByRole("button", { name: "Add to knowledge base" }));
  expect(await screen.findByText("pets.md: added: pets.md")).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: "Dismiss" }));
  expect(screen.queryByText("pets.md: added: pets.md")).toBeNull();

  await userEvent.click(screen.getByRole("button", { name: "Delete sample_policy.md" }));
  expect(await screen.findByText("Deleted sample_policy.md")).toBeInTheDocument();
  expect(api.calls.some((c) => c.method === "DELETE")).toBe(true);
});
