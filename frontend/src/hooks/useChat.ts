/**
 * The conversation use case: ask by text or voice, keep the history, retry a failed answer,
 * stop an answer in flight, start a new conversation, and read answers aloud according to the
 * reply mode. Only one request is in flight at a time; starting over cancels it.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useClient } from "../api/ClientContext";
import { isCancelled, messageOf } from "../api/errors";
import { speech } from "../lib/speech";
import { newId } from "../lib/text";
import type { Message, ReplyMode } from "../types";

export type ChatActivity = "idle" | "transcribing" | "thinking";

interface Options {
  userId: string;
  replyMode: ReplyMode;
  rate: number;
}

export function useChat(options: Options) {
  const client = useClient();
  const [messages, setMessages] = useState<Message[]>([]);
  const [activity, setActivity] = useState<ChatActivity>("idle");
  const [notice, setNotice] = useState<string | null>(null);
  const session = useRef(newId());
  const inflight = useRef<AbortController | null>(null);
  const recordings = useRef<string[]>([]);
  const latest = useRef(options);

  useEffect(() => {
    latest.current = options;
  });

  /** Cancels whatever is running and returns a controller for the next request. */
  const begin = useCallback((next: ChatActivity) => {
    inflight.current?.abort();
    const controller = new AbortController();
    inflight.current = controller;
    setNotice(null);
    setActivity(next);
    return controller;
  }, []);

  const finish = useCallback((controller: AbortController) => {
    if (inflight.current === controller) inflight.current = null;
    setActivity("idle");
  }, []);

  /** Ask the backend; adds the answer (or the failure) unless the request was cancelled. */
  const answer = useCallback(
    async (question: string, spoken: boolean) => {
      const controller = begin("thinking");
      let reply: Message;
      try {
        const result = await client.chat(
          latest.current.userId,
          question,
          session.current,
          controller.signal,
        );
        reply = assistantMessage(question, result.response || "_(no response)_", {
          sources: result.sources,
          toolCalls: result.tool_calls,
        });
      } catch (error) {
        if (isCancelled(error)) return;
        reply = assistantMessage(question, messageOf(error), { error: true });
      }
      finish(controller);
      setMessages((m) => [...m, reply]);

      const { replyMode, rate } = latest.current;
      if (!reply.error && (replyMode === "always" || (replyMode === "auto" && spoken))) {
        speech.speak(reply.id, reply.content, rate);
      }
    },
    [client, begin, finish],
  );

  const ask = useCallback(
    async (question: string, recordingUrl?: string) => {
      const text = question.trim();
      if (!text) return;
      setMessages((m) => [...m, userMessage(text, recordingUrl)]);
      await answer(text, recordingUrl !== undefined);
    },
    [answer],
  );

  const askByVoice = useCallback(
    async (audio: Blob, filename: string) => {
      const controller = begin("transcribing");
      let question: string;
      try {
        question = await client.transcribe(audio, filename, controller.signal);
      } catch (error) {
        if (!isCancelled(error)) {
          finish(controller);
          setNotice(messageOf(error));
        }
        return;
      }
      finish(controller);
      const url = URL.createObjectURL(audio);
      recordings.current.push(url);
      await ask(question, url);
    },
    [client, begin, finish, ask],
  );

  /** Replace a failed answer with a fresh attempt at the same question. */
  const retry = useCallback(
    async (failed: Message) => {
      if (!failed.question) return;
      setMessages((m) => m.filter((x) => x.id !== failed.id));
      await answer(failed.question, false);
    },
    [answer],
  );

  /** Stop the answer (or transcription) in flight. The question stays in the chat. */
  const cancel = useCallback(() => {
    inflight.current?.abort();
    inflight.current = null;
    setActivity("idle");
  }, []);

  const reset = useCallback(() => {
    cancel();
    speech.stop();
    recordings.current.forEach((url) => {
      URL.revokeObjectURL(url);
    });
    recordings.current = [];
    setMessages([]);
    setNotice(null);
    session.current = newId();
  }, [cancel]);

  return { messages, activity, notice, ask, askByVoice, retry, cancel, reset };
}

function userMessage(content: string, audioUrl?: string): Message {
  const voice = audioUrl !== undefined;
  return { id: newId(), role: "user", content, sources: [], toolCalls: [], voice, audioUrl };
}

function assistantMessage(
  question: string,
  content: string,
  extra: Partial<Pick<Message, "sources" | "toolCalls" | "error">>,
): Message {
  return {
    id: newId(),
    role: "assistant",
    content,
    question,
    sources: extra.sources ?? [],
    toolCalls: extra.toolCalls ?? [],
    error: extra.error,
  };
}
