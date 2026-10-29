/** Pure text helpers (no React, no DOM), so they are trivially unit-testable. */
import type { SyncReport } from "../types";

const CITATION = /\s*\[([^\]]*§[^\]]*)\]/g; // [file § section]
const MARKDOWN = /[*_`#>|]/g;
const EMOJI = /[\u{1F300}-\u{1FAFF}☀-➿]/gu;
const SPACE_BEFORE_PUNCT = /\s+([.,;:!?؟])/g;
const SUPERSCRIPT = "⁰¹²³⁴⁵⁶⁷⁸⁹";

export function citationMark(n: number): string {
  return String(n)
    .split("")
    .map((d) => SUPERSCRIPT[Number(d)])
    .join("");
}

/** Replace inline `[file § section]` citations with superscript numbers matching the
 * numbered source tags under the answer. Citations that aren't in `sources` stay as written. */
export function numberCitations(text: string, sources: string[]): string {
  return text.replace(CITATION, (match, inner: string) => {
    const cited = inner.split(";").map((c) => c.trim());
    if (!cited.every((c) => sources.includes(c))) return match;
    return cited.map((c) => citationMark(sources.indexOf(c) + 1)).join("");
  });
}

/** "sample_policy.md § Section 1: Water" -> { document, section } */
export function splitCitation(source: string): { document: string; section: string | null } {
  const at = source.indexOf(" § ");
  if (at < 0) return { document: source, section: null };
  return { document: source.slice(0, at), section: source.slice(at + 3) };
}

/** Strip citations, markdown and emoji so text-to-speech reads only the answer. */
export function speakable(text: string): string {
  return text
    .replace(CITATION, "")
    .replace(/[¹²³⁴⁵⁶⁷⁸⁹⁰]/g, "")
    .replace(MARKDOWN, "")
    .replace(EMOJI, "")
    .replace(/\s+/g, " ")
    .replace(SPACE_BEFORE_PUNCT, "$1")
    .trim();
}

export function isArabic(text: string): boolean {
  return /[؀-ۿ]/.test(text);
}

/** Sentences, so long answers aren't cut off (Chrome stops one utterance after ~15 s). */
export function sentences(text: string): string[] {
  const parts = text.match(/[^.!?؟\n]+[.!?؟]*/g) ?? [text];
  return parts.map((s) => s.trim()).filter(Boolean);
}

export function summarizeSync(report: SyncReport): string {
  const parts = (["added", "updated", "removed"] as const)
    .filter((k) => report[k].length)
    .map((k) => `${k}: ${report[k].join(", ")}`);
  for (const [name, why] of Object.entries(report.failed)) parts.push(`failed: ${name} (${why})`);
  return parts.join("; ") || "No changes - everything was already indexed.";
}

export function plural(count: number, noun: string): string {
  return `${count} ${noun}${count === 1 ? "" : "s"}`;
}

export function newId(): string {
  return Math.random().toString(36).slice(2, 14);
}
