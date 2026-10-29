import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ClientProvider } from "../api/ClientContext";
import { OmniCareClient } from "../api/client";
import type { Preferences } from "../hooks/usePreferences";
import { DOCUMENTS, fakeFetch, json } from "../test/fakes";
import { Sidebar } from "./Sidebar";

function prefs(overrides: Partial<Preferences> = {}): Preferences {
  return {
    userId: "usr_123",
    setUserId: vi.fn(),
    replyMode: "auto",
    setReplyMode: vi.fn(),
    rate: 1,
    setRate: vi.fn(),
    theme: "system",
    setTheme: vi.fn(),
    ...overrides,
  };
}

function renderSidebar(p: Preferences, open = true, onClose = vi.fn()) {
  const api = fakeFetch({ "GET /api/v1/documents": () => json(DOCUMENTS) });
  render(
    <ClientProvider client={new OmniCareClient("", api.impl)}>
      <Sidebar prefs={p} open={open} onClose={onClose} onNewConversation={vi.fn()} />
    </ClientProvider>,
  );
  return onClose;
}

it("changes the reply mode and speaking speed", async () => {
  const p = prefs();
  renderSidebar(p);
  await userEvent.click(screen.getByText("Voice replies"));
  await userEvent.click(screen.getByLabelText("Always"));
  expect(p.setReplyMode).toHaveBeenCalledWith("always");

  fireEvent.change(screen.getByRole("slider"), { target: { value: "1.25" } });
  expect(p.setRate).toHaveBeenCalledWith(1.25);
});

it("trims the user id and flags an invalid one", async () => {
  const p = prefs({ userId: "bad id!" });
  renderSidebar(p);
  expect(screen.getByText("Letters, numbers, - and _ only.")).toBeInTheDocument();
  expect(screen.getByRole("textbox", { name: /User ID/ })).toHaveAttribute("aria-invalid", "true");

  await userEvent.type(screen.getByRole("textbox", { name: /User ID/ }), " ");
  expect(p.setUserId).toHaveBeenLastCalledWith("bad id!");
});

it("moves focus into the open drawer and closes on Escape", async () => {
  const onClose = renderSidebar(prefs());
  expect(screen.getByRole("button", { name: "Close settings" })).toHaveFocus();
  await userEvent.keyboard("{Escape}");
  expect(onClose).toHaveBeenCalled();
});

it("ignores Escape while closed", async () => {
  const onClose = renderSidebar(prefs(), false);
  await userEvent.keyboard("{Escape}");
  expect(onClose).not.toHaveBeenCalled();
});
