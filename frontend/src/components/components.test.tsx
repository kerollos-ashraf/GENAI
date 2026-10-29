import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { filenameFor } from "../hooks/useRecorder";
import type { Message } from "../types";
import { Citations } from "./Citations";
import { Composer } from "./Composer";
import { Intro } from "./Intro";
import { MessageBubble } from "./MessageBubble";

const WATER = "sample_policy.md § Section 1: Home Water Damage Coverage";

function answer(overrides: Partial<Message> = {}): Message {
  return {
    id: "a1",
    role: "assistant",
    content: `Covered up to **$25,000** [${WATER}].`,
    sources: [WATER],
    toolCalls: [
      { name: "search_policy", args: { query: "pipe" }, status: "success", output: "passages" },
    ],
    ...overrides,
  };
}

describe("MessageBubble", () => {
  it("shows the answer with a numbered marker instead of the raw citation", () => {
    render(<MessageBubble message={answer()} rate={1} />);
    const bubble = screen.getByTestId("message");
    expect(bubble).toHaveTextContent("Covered up to $25,000¹.");
    expect(bubble).not.toHaveTextContent("[sample_policy.md");
    expect(screen.getByText("$25,000").tagName).toBe("STRONG"); // markdown rendered, no maths
  });

  it("lists tool calls with their arguments and output", () => {
    render(<MessageBubble message={answer()} rate={1} />);
    expect(screen.getByText("Tool calls (1)")).toBeInTheDocument();
    expect(screen.getByText("search_policy")).toBeInTheDocument();
    expect(screen.getByText("passages")).toBeInTheDocument();
  });

  it("shows errors plainly, with Try again but no citations, player or copy", async () => {
    const onRetry = vi.fn();
    const failed = answer({
      content: "Backend error 502: down",
      error: true,
      sources: [],
      question: "Are floods covered?",
    });
    render(<MessageBubble message={failed} rate={1} onRetry={onRetry} />);
    expect(screen.getByTestId("message")).toHaveTextContent("Backend error 502: down");
    expect(screen.queryByLabelText("Sources")).toBeNull();
    expect(screen.queryByRole("button", { name: "Copy answer" })).toBeNull();

    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(onRetry).toHaveBeenCalledWith(failed);
  });

  it("offers no Try again when the failed question is unknown", () => {
    render(
      <MessageBubble message={answer({ content: "x", error: true })} rate={1} onRetry={vi.fn()} />,
    );
    expect(screen.queryByRole("button", { name: "Try again" })).toBeNull();
  });

  it("opens model links in a new tab without leaking the opener", () => {
    render(
      <MessageBubble
        message={answer({ content: "See [the policy](https://example.com)." })}
        rate={1}
      />,
    );
    const link = screen.getByRole("link", { name: "the policy" });
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noreferrer");
  });

  it("marks spoken questions", () => {
    render(
      <MessageBubble
        message={{ ...answer(), role: "user", content: "Hi", voice: true }}
        rate={1}
      />,
    );
    expect(screen.getByText("Spoken question")).toBeInTheDocument();
  });

  it("does not render HTML from the model", () => {
    render(
      <MessageBubble
        message={answer({ content: "<img src=x onerror=alert(1)> ok", sources: [] })}
        rate={1}
      />,
    );
    expect(document.querySelector("img")).toBeNull();
  });
});

it("Citations shows each section once, numbered, with its file", () => {
  render(<Citations sources={[WATER, "notes.txt"]} />);
  const items = screen.getAllByRole("listitem");
  expect(items[0]).toHaveTextContent("§¹Section 1: Home Water Damage Coveragesample_policy.md");
  expect(items[1]).toHaveTextContent("§²notes.txt");
});

describe("Composer", () => {
  it("sends on Enter, keeps Shift+Enter for new lines, then clears", async () => {
    const onSend = vi.fn();
    render(<Composer busy={false} notice={null} onSend={onSend} onVoice={vi.fn()} />);
    const box = screen.getByTestId("composer-input");
    await userEvent.type(box, "Line one{Shift>}{Enter}{/Shift}line two{Enter}");
    expect(onSend).toHaveBeenCalledWith("Line one\nline two");
    expect(box).toHaveValue("");
  });

  it("does not send blank text or while busy", async () => {
    const onSend = vi.fn();
    const { rerender } = render(
      <Composer busy={false} notice={null} onSend={onSend} onVoice={vi.fn()} />,
    );
    await userEvent.type(screen.getByTestId("composer-input"), "   {Enter}");
    rerender(<Composer busy notice={null} onSend={onSend} onVoice={vi.fn()} />);
    await userEvent.type(screen.getByTestId("composer-input"), "hi{Enter}");
    expect(onSend).not.toHaveBeenCalled();
  });

  it("shows a character counter only near the limit", async () => {
    render(<Composer busy={false} notice={null} onSend={vi.fn()} onVoice={vi.fn()} />);
    const box = screen.getByTestId("composer-input");
    expect(screen.queryByText(/\/ 2,000/)).toBeNull();
    await userEvent.click(box);
    await userEvent.paste("x".repeat(1850));
    expect(screen.getByText("1,850 / 2,000")).toBeInTheDocument();
  });

  it("shows a notice", () => {
    render(
      <Composer busy={false} notice="No speech detected" onSend={vi.fn()} onVoice={vi.fn()} />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("No speech detected");
  });
});

it("Intro suggestions ask their full question", async () => {
  const onAsk = vi.fn();
  render(<Intro onAsk={onAsk} disabled={false} />);
  await userEvent.click(screen.getByRole("button", { name: "Check claim CLM-8821" }));
  expect(screen.getAllByRole("button")).toHaveLength(4);
  expect(onAsk).toHaveBeenCalledWith("What's the status of claim CLM-8821?");
});

it("names recordings by their audio type", () => {
  expect(filenameFor("audio/webm;codecs=opus")).toBe("question.webm");
  expect(filenameFor("audio/mp4")).toBe("question.m4a");
  expect(filenameFor("audio/ogg")).toBe("question.ogg");
});
