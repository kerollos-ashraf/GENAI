import type { ComponentProps } from "react";
import Markdown, { type Components } from "react-markdown";
import { useClipboard } from "../hooks/useClipboard";
import { numberCitations, speakable } from "../lib/text";
import type { Message } from "../types";
import { Citations } from "./Citations";
import { Icon } from "./Icon";
import "./Message.css";
import { ToolCalls } from "./ToolCalls";
import { VoicePlayer } from "./VoicePlayer";

/** Links from the model open in a new tab; raw HTML is never rendered (react-markdown default). */
const MARKDOWN: Components = {
  a: ({ children, ...props }: ComponentProps<"a">) => (
    <a {...props} target="_blank" rel="noreferrer">
      {children}
    </a>
  ),
};

interface Props {
  message: Message;
  rate: number;
  onRetry?: (message: Message) => void;
}

export function MessageBubble({ message, rate, onRetry }: Props) {
  const isUser = message.role === "user";
  return (
    <article
      className={`message ${message.role}${message.error ? " error" : ""}`}
      data-testid="message"
      data-role={message.role}
      aria-label={isUser ? "Your question" : "Answer"}
    >
      <span className="avatar" aria-hidden="true">
        <Icon name={isUser ? "person" : "shield"} size={17} />
      </span>
      <div className="bubble">
        {isUser ? (
          <UserContent message={message} />
        ) : message.error ? (
          <FailedAnswer message={message} onRetry={onRetry} />
        ) : (
          <Answer message={message} rate={rate} />
        )}
      </div>
    </article>
  );
}

function UserContent({ message }: { message: Message }) {
  return (
    <>
      {message.voice && <span className="spoken">Spoken question</span>}
      <p>{message.content}</p>
      {message.audioUrl && (
        // The transcript is the text right above, so the recording needs no caption track.
        // eslint-disable-next-line jsx-a11y/media-has-caption
        <audio className="recording" controls src={message.audioUrl} aria-label="Your recording" />
      )}
    </>
  );
}

function Answer({ message, rate }: { message: Message; rate: number }) {
  return (
    <>
      <div className="answer">
        <Markdown components={MARKDOWN}>
          {numberCitations(message.content, message.sources)}
        </Markdown>
      </div>
      <Citations sources={message.sources} />
      <div className="answer-actions">
        <VoicePlayer id={message.id} text={message.content} rate={rate} />
        <CopyButton text={speakable(message.content)} />
      </div>
      <ToolCalls calls={message.toolCalls} />
    </>
  );
}

function FailedAnswer({ message, onRetry }: Pick<Props, "message" | "onRetry">) {
  return (
    <>
      <p className="error-text">
        <Icon name="alert" size={16} /> {message.content}
      </p>
      {onRetry && message.question && (
        <button
          className="chip-button retry"
          onClick={() => {
            onRetry(message);
          }}
        >
          <Icon name="refresh" size={14} /> Try again
        </button>
      )}
    </>
  );
}

function CopyButton({ text }: { text: string }) {
  const { copied, copy } = useClipboard();
  return (
    <button
      className="chip-button"
      onClick={() => void copy(text)}
      aria-label={copied ? "Copied" : "Copy answer"}
    >
      <Icon name={copied ? "check" : "copy"} size={14} />
      <span aria-hidden="true">{copied ? "Copied" : "Copy"}</span>
    </button>
  );
}

export function Thinking({ label, onStop }: { label: string; onStop: () => void }) {
  return (
    <article className="message assistant" data-testid="thinking">
      <span className="avatar" aria-hidden="true">
        <Icon name="shield" size={17} />
      </span>
      <div className="bubble thinking" role="status">
        <span className="dots" aria-hidden="true">
          <i />
          <i />
          <i />
        </span>
        {label}
        <button className="chip-button" onClick={onStop}>
          <Icon name="stop" size={10} /> Stop
        </button>
      </div>
    </article>
  );
}
