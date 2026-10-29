"""Prompt-injection screening (an `InputGuard` implementation).

Defence in depth - this is one of five layers:
  1. API        - Pydantic limits on message size and user_id format.
  2. This guard - deterministic patterns for well-known injection / jailbreak phrasing, in
                  English and Arabic, applied to user messages (typed or spoken) AND to every
                  document before it is indexed (uploads and files dropped in the folder).
  3. Prompt     - retrieved text and tool output are declared to be data, not instructions.
  4. Tools      - Pydantic validation on every argument, so a manipulated model still can't
                  write malformed data.
  5. Memory     - blocked messages are redacted so they never reach the model later.

The patterns target instructions aimed *at the assistant* ("ignore your/previous
instructions", "you are now…", "act as an admin"), not ordinary words: real customers say
"can my wife act as the claimant?" or "should I ignore the rules about receipts?", and a
customer-facing assistant must not refuse them. `tests/test_guardrails.py` pins both sides.
"""

import re
import unicodedata
from dataclasses import dataclass

REFUSAL_MESSAGE = (
    "I can't help with that request. I'm OmniCare's policy assistant: I can answer "
    "coverage questions, check a claim's status, or help you file a new claim."
)

# Words that make an instruction refer to the assistant's own configuration.
_TARGET = r"(previous|prior|above|earlier|preceding|your|all|any|every|the system'?s?|these|those)"
_INSTRUCTIONS = r"(instruction|rule|prompt|guideline|direction|guardrail|polic(y|ies))s?"
_PRIVILEGED = (
    r"(admin|administrator|developer|system|root|superuser|unrestricted|unfiltered|jailbroken|dan)"
)

DEFAULT_PATTERNS: dict[str, str] = {
    # "ignore all previous instructions", "disregard your rules", "forget the instructions above"
    "override": (
        rf"\b(ignore|disregard|forget|override|bypass|skip)\b.{{0,30}}\b{_TARGET}\b.{{0,20}}\b{_INSTRUCTIONS}\b"
        rf"|\b(ignore|disregard|forget|override|bypass)\b.{{0,30}}\b{_INSTRUCTIONS}\b.{{0,15}}\b(above|before|earlier|so far)\b"
    ),
    # "reveal your system prompt", "print everything above", "what were you told before…"
    "prompt_leak": (
        r"\b(reveal|show|print|repeat|output|tell me|what (is|are)|dump|leak)\b.{0,30}"
        r"\b(system|hidden|initial|original|developer|secret)\s+(prompt|message|instruction)s?"
        r"|\b(print|repeat|output|show|copy|dump)\b.{0,30}\b(everything|all|text|words)\b.{0,20}\b(above|before this|so far)\b"
        r"|\bwhat (were|have) you (been )?(told|instructed|given|programmed)\b"
        r"|\b(rules|instructions|prompt)\b.{0,20}\byou (were|have been) (given|told)\b"
    ),
    # "you are now…", "from now on you will…", "act as an admin", "pretend you are…"
    "role_hijack": (
        r"\byou are now\b"
        r"|\bfrom now on,? you (are|will|must|should|shall|have to)\b"
        rf"|\b(act|behave|respond|operate) as (if you (are|were) )?(an? |the )?{_PRIVILEGED}\b"
        r"|\bpretend (to be|you are|you're)\b|\broleplay as\b"
    ),
    "jailbreak": r"\b(jailbreak|dan mode|developer mode|god mode|do anything now|no restrictions)\b",
    "fake_role_tag": r"(<\|?(im_start|system|assistant)\|?>|\[/?(system|inst)\]|^\s*(system|assistant)\s*:)",
    "tool_abuse": r"\b(mark|change|set|update|modify|force)\b.{0,40}\b(to|as)\s+(approved|paid|settled)\b",
    # Arabic (matched after normalisation: no diacritics/tatweel, alef and yaa variants unified)
    "override_ar": (
        r"(تجاهل|تجاهلي|انس|انسي|انسى|تخط|تخطي|تجاوز|اهمل|الغ)\s.{0,30}"
        r"(التعليمات|القواعد|الاوامر|التوجيهات|التعليمات السابقه)"
    ),
    "prompt_leak_ar": (
        r"(اكشف|اعرض|اطبع|اظهر|كرر|اخبرني|ما هي|ما هو).{0,30}"
        r"(موجه النظام|تعليمات النظام|رساله النظام|التعليمات المخفيه|التعليمات الاصليه|التعليمات السريه)"
    ),
    "role_hijack_ar": (
        r"(انت الان|من الان فصاعدا انت|تظاهر بانك|تصرف ك(مسؤول|مدير|مطور|نظام))"
    ),
}  # fmt: skip

_ZERO_WIDTH = re.compile(r"[\u200b-\u200f\u2060\ufeff]")
_ARABIC_MARKS = re.compile(
    r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]"
)  # harakat, tatweel
_ARABIC_LETTERS = str.maketrans(
    {
        "\u0623": "\u0627",
        "\u0625": "\u0627",
        "\u0622": "\u0627",
        "\u0671": "\u0627",
        "\u0649": "\u064a",
        "\u0629": "\u0647",
    }
)  # alef/yaa/taa marbuta variants


@dataclass(frozen=True)
class GuardResult:
    allowed: bool
    reason: str | None = None


class PatternInjectionGuard:
    """Regex-based guard. Patterns are injectable, so rules can be extended without editing
    this class (Open/Closed), and another guard - e.g. an LLM classifier - can implement the
    same `InputGuard` protocol."""

    def __init__(self, patterns: dict[str, str] | None = None) -> None:
        self._rules = [
            (name, re.compile(rx, re.IGNORECASE | re.MULTILINE))
            for name, rx in (patterns or DEFAULT_PATTERNS).items()
        ]

    @staticmethod
    def normalise(text: str) -> str:
        """NFKC folds full-width / stylised characters; zero-width characters (used to split
        words) are removed; Arabic diacritics and letter variants are unified."""
        text = _ZERO_WIDTH.sub("", unicodedata.normalize("NFKC", text))
        return _ARABIC_MARKS.sub("", text).translate(_ARABIC_LETTERS)

    def check(self, text: str) -> GuardResult:
        normalised = self.normalise(text)
        for name, rule in self._rules:
            if rule.search(normalised):
                return GuardResult(allowed=False, reason=name)
        return GuardResult(allowed=True)
