/** Knowledge-base management: list, upload, delete, re-index - with a one-line outcome. */
import { useCallback, useEffect, useState } from "react";
import { useClient } from "../api/ClientContext";
import { messageOf } from "../api/errors";
import { summarizeSync } from "../lib/text";
import type { DocumentList } from "../types";

export interface Outcome {
  ok: boolean;
  text: string;
}

export function useKnowledgeBase() {
  const client = useClient();
  const [list, setList] = useState<DocumentList | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [busy, setBusy] = useState(false);
  const [outcome, setOutcome] = useState<Outcome | null>(null);

  const refresh = useCallback(async () => {
    try {
      setList(await client.listDocuments());
      setUnavailable(false);
    } catch {
      setUnavailable(true);
    }
  }, [client]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const run = useCallback(
    async (action: () => Promise<Outcome>) => {
      setBusy(true);
      setOutcome(null);
      try {
        setOutcome(await action());
      } catch (error) {
        setOutcome({ ok: false, text: messageOf(error) });
      } finally {
        setBusy(false);
        await refresh();
      }
    },
    [refresh],
  );

  const upload = (files: File[]) =>
    run(async () => {
      const lines: string[] = [];
      let ok = true;
      for (const file of files) {
        try {
          const report = await client.uploadDocument(file, file.name);
          lines.push(`${file.name}: ${summarizeSync(report)}`);
        } catch (error) {
          ok = false;
          lines.push(`${file.name}: ${messageOf(error)}`);
        }
      }
      return { ok, text: lines.join("\n") };
    });

  const remove = (filename: string) =>
    run(async () => {
      await client.deleteDocument(filename);
      return { ok: true, text: `Deleted ${filename}` };
    });

  const reindex = () =>
    run(async () => ({ ok: true, text: summarizeSync(await client.reindex()) }));

  const dismiss = () => {
    setOutcome(null);
  };

  return { list, unavailable, busy, outcome, upload, remove, reindex, dismiss };
}
