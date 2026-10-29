import {
  citationMark,
  numberCitations,
  plural,
  sentences,
  speakable,
  splitCitation,
  summarizeSync,
} from "./text";

const WATER = "p.md § Section 1: Water";
const THEFT = "p.md § Section 2: Theft";

describe("numberCitations", () => {
  it("replaces known citations with superscripts matching the source tags", () => {
    const text = `Covered [${WATER}]. Theft too [${THEFT}; ${WATER}]. Other [x.md § Gone].`;
    expect(numberCitations(text, [WATER, THEFT])).toBe(
      "Covered¹. Theft too²¹. Other [x.md § Gone].",
    );
  });

  it("leaves text without citations alone", () => {
    expect(numberCitations("Plain $25,000 answer.", [])).toBe("Plain $25,000 answer.");
  });

  it("numbers past nine", () => {
    expect(citationMark(12)).toBe("¹²");
  });
});

describe("splitCitation", () => {
  it("separates document and section", () => {
    expect(splitCitation(WATER)).toEqual({ document: "p.md", section: "Section 1: Water" });
    expect(splitCitation("notes.txt")).toEqual({ document: "notes.txt", section: null });
  });
});

describe("speakable", () => {
  it("strips citations, markers, markdown and emoji", () => {
    const answer = `Yes - covered up to **$25,000** [${WATER}]. Floods 🌊 excluded¹.`;
    expect(speakable(answer)).toBe("Yes - covered up to $25,000. Floods excluded.");
  });
});

describe("sentences", () => {
  it("splits English and Arabic sentences", () => {
    expect(sentences("One. Two? Three!")).toEqual(["One.", "Two?", "Three!"]);
    expect(sentences("هل هذا مغطى؟ نعم.")).toEqual(["هل هذا مغطى؟", "نعم."]);
  });
});

describe("summarizeSync", () => {
  it("describes what changed", () => {
    const report = {
      added: ["a.md"],
      updated: [],
      removed: ["b.pdf"],
      unchanged: [],
      failed: { "c.pdf": "bad" },
    };
    expect(summarizeSync(report)).toBe("added: a.md; removed: b.pdf; failed: c.pdf (bad)");
  });

  it("says when nothing changed", () => {
    const empty = { added: [], updated: [], removed: [], unchanged: ["a.md"], failed: {} };
    expect(summarizeSync(empty)).toBe("No changes - everything was already indexed.");
  });
});

it("pluralises", () => {
  expect(plural(1, "passage")).toBe("1 passage");
  expect(plural(3, "passage")).toBe("3 passages");
});
