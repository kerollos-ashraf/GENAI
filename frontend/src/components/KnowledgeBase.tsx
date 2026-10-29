import { useRef, useState } from "react";
import { DOCUMENT_TYPES } from "../config";
import { useKnowledgeBase } from "../hooks/useKnowledgeBase";
import { plural } from "../lib/text";
import { Icon } from "./Icon";
import "./KnowledgeBase.css";

/** See indexed documents, upload new ones, delete, re-index. */
export function KnowledgeBase() {
  const kb = useKnowledgeBase();
  const [files, setFiles] = useState<File[]>([]);
  const picker = useRef<HTMLInputElement>(null);

  const add = async () => {
    await kb.upload(files);
    setFiles([]);
    if (picker.current) picker.current.value = "";
  };

  return (
    <details className="panel" data-testid="knowledge-base">
      <summary>
        <Icon name="books" /> Knowledge base
      </summary>
      {kb.outcome && (
        <div className={`outcome ${kb.outcome.ok ? "ok" : "fail"}`} role="status">
          <p>{kb.outcome.text}</p>
          <button className="icon-button" onClick={kb.dismiss} aria-label="Dismiss">
            <Icon name="close" size={14} />
          </button>
        </div>
      )}
      <DocumentList kb={kb} />

      <label className="file-picker">
        <Icon name="upload" size={16} />
        <span>
          {files.length
            ? files.map((f) => f.name).join(", ")
            : "Choose PDF, Markdown or text files"}
        </span>
        <input
          ref={picker}
          type="file"
          multiple
          accept={DOCUMENT_TYPES.join(",")}
          data-testid="document-input"
          onChange={(e) => {
            setFiles(Array.from(e.target.files ?? []));
          }}
        />
      </label>
      <button className="button" onClick={() => void add()} disabled={!files.length || kb.busy}>
        {kb.busy ? "Working…" : "Add to knowledge base"}
      </button>
      <button className="button quiet" onClick={() => void kb.reindex()} disabled={kb.busy}>
        <Icon name="refresh" size={16} /> Re-index all documents
      </button>
    </details>
  );
}

function DocumentList({ kb }: { kb: ReturnType<typeof useKnowledgeBase> }) {
  if (kb.unavailable) return <p className="muted">Unavailable - the backend can't be reached.</p>;
  if (!kb.list) return <p className="muted">Loading…</p>;
  const { documents, total_chunks } = kb.list;
  return (
    <>
      <p className="muted">
        {plural(documents.length, "document")}, {plural(total_chunks, "passage")} searchable
      </p>
      <ul className="docs">
        {documents.map((doc) => (
          <li key={doc.filename} className="doc" data-testid="document">
            <Icon name="doc" size={16} />
            <div>
              <b>{doc.filename}</b>
              <span>{doc.indexed ? plural(doc.chunks, "passage") : "Not indexed yet"}</span>
            </div>
            <button
              className="icon-button"
              onClick={() => void kb.remove(doc.filename)}
              disabled={kb.busy}
              aria-label={`Delete ${doc.filename}`}
            >
              <Icon name="trash" size={16} />
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}
