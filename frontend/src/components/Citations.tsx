import { citationMark, splitCitation } from "../lib/text";

/** Numbered source tags: a highlighter mark on the policy section the answer came from. */
export function Citations({ sources }: { sources: string[] }) {
  if (!sources.length) return null;
  return (
    <ul className="cites" aria-label="Sources">
      {sources.map((source, i) => {
        const { document, section } = splitCitation(source);
        return (
          <li key={source} className="cite" title={source}>
            <b>§{citationMark(i + 1)}</b>
            <span>{section ?? document}</span>
            {section && <small>{document}</small>}
          </li>
        );
      })}
    </ul>
  );
}
