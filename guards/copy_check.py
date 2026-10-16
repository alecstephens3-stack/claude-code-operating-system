#!/usr/bin/env python3
"""copy_check.py: the mechanical half of the review on anything that goes out.

The problem: a model writes a confident, well-formatted draft and calls it
done. The draft can still carry a number nobody measured, a tool the business
stopped using months ago, or the filler and punctuation the owner has banned.
A person then has to catch all of that by eye, every time.

So the rules that have one right answer live here, in code, and every outgoing
surface runs through them:

  FAIL    one right answer: em and en dashes, banned phrases, retired tools in
          anything we send, and the per-surface rules below. Exit code 1.
  VERIFY  every number with a unit ("40 hours", "12%") that does not appear in
          a proof file. Phrasing varies, so this is a prompt to check the
          number, never a claim that it is wrong. VERIFY never fails the run.

Whether the right proof was chosen and whether a reader would believe it are
judgment calls. Those go to a reviewer agent. This script does not pretend to
cover them.

Profiles:
  email     short, a greeting, a sign-off, about one exclamation point
  proposal  word range, no pricing, no greeting line, does not open with "I",
            ends on a question
  artifact  an HTML page: tags, scripts and styles are stripped first, then
            only the shared checks run

    python3 guards/copy_check.py draft.txt --profile email
    python3 guards/copy_check.py page.html --profile artifact
    cat draft.txt | python3 guards/copy_check.py - --profile proposal

The rules (banned phrases, retired tools, limits, which files count as proof)
live in copy_rules.json, so the check and the writing rules cannot disagree.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RULES = Path(__file__).resolve().parent / "copy_rules.json"
PROFILES = ("email", "proposal", "artifact")
DASHES = (("\u2014", "an em dash"), ("\u2013", "an en dash"))
GREETINGS = ("hi", "hello", "hey", "dear", "greetings", "good morning", "good afternoon")

# A number carrying a unit is a factual claim. A bare integer ("3 options") is not.
# The unit alternatives sit inside the group so "93%." at the end of a sentence
# still matches: there is no word boundary between "%" and ".".
UNIT_WORDS = (
    "percent", "hours", "hour", "hrs", "hr", "minutes", "minute", "mins", "min",
    "days", "day", "weeks", "week", "months", "month", "years", "year",
    "pages", "page", "staff", "people", "employees", "employee",
    "clients", "client", "invoices", "invoice", "orders", "order",
)
CLAIM = re.compile(r"\b\d[\d,.]*[ \t]*(?:%|(?:" + "|".join(UNIT_WORDS) + r")\b)", re.I)

# Different spellings of the same unit. A claim is compared as (number, family),
# so "8 hrs" in a draft matches "8 hours" in the proof file.
FAMILY = {
    "%": "percent", "percent": "percent",
    "hour": "hour", "hours": "hour", "hr": "hour", "hrs": "hour",
    "minute": "minute", "minutes": "minute", "min": "minute", "mins": "minute",
    "day": "day", "days": "day", "week": "week", "weeks": "week",
    "month": "month", "months": "month", "year": "year", "years": "year",
    "page": "page", "pages": "page",
    "staff": "person", "people": "person", "employee": "person", "employees": "person",
    "client": "client", "clients": "client", "invoice": "invoice", "invoices": "invoice",
    "order": "order", "orders": "order",
}

PRICING = (
    re.compile(r"\$\s?\d[\d,.]*"),
    re.compile(r"[\u00a3\u20ac\u00a5]\s?\d"),
    re.compile(r"\b\d+\s*(?:/|per\s+)(?:hr|hour|day|week|month)\b", re.I),
    re.compile(r"\b(?:hourly rate|my rate|day rate|starting at)\b", re.I),
)


def load_rules(path: Path = DEFAULT_RULES) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def proof_corpus(root: Path, rules: dict) -> tuple[str, list[str]]:
    """Everything a number is allowed to come from: files a person keeps as the record."""
    parts, read = [], []
    for pattern in rules.get("proof_files", []):
        for p in sorted(root.glob(pattern)):
            if p.is_file():
                parts.append(p.read_text(encoding="utf-8", errors="ignore"))
                read.append(p.relative_to(root).as_posix())
    return "\n".join(parts), read


def as_pair(claim: str) -> tuple[str, str] | None:
    s = claim.lower().strip().replace(",", "")
    m = re.match(r"(\d[\d.]*)\s*(%|[a-z]+)", s)
    if not m:
        return None
    family = FAMILY.get(m.group(2))
    return (m.group(1).rstrip("."), family) if family else None


def claim_pairs(text: str) -> set[tuple[str, str]]:
    return {pair for m in CLAIM.finditer(text) if (pair := as_pair(m.group(0)))}


def words(text: str) -> int:
    return len(text.split())


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def strip_html(raw: str) -> str:
    """Prose only. Scripts, styles and inline SVG carry numbers that are not claims."""
    out = re.sub(r"(?is)<(script|style|svg)\b.*?</\1>", " ", raw)
    out = re.sub(r"(?s)<!--.*?-->", " ", out)
    out = re.sub(r"(?s)<[^>]+>", " ", out)
    for ent, ch in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                    ("&quot;", '"'), ("&#39;", "'")):
        out = out.replace(ent, ch)
    return re.sub(r"[ \t]+", " ", out)


def shared_checks(text: str, profile: str, rules: dict, corpus: str) -> tuple[list[str], list[str]]:
    hard: list[str] = []
    verify: list[str] = []
    low = text.lower()
    sending = profile in ("email", "proposal")

    for ch, name in DASHES:
        if ch in text:
            hard.append(f"DASH      contains {name}. Use a period, comma or colon")

    for phrase, why in rules.get("banned_phrases", {}).items():
        if re.search(r"(?<![\w'])" + re.escape(phrase) + r"(?![\w'])", low):
            hard.append(f"BANNED    contains {phrase!r}: {why}")

    for family in rules.get("banned_word_families", {}).values():
        for m in re.finditer(r"\b(" + "|".join(map(re.escape, family["forms"])) + r")\b", low):
            hard.append(f"BANNED    contains {m.group(0)!r}: {family['why']}")

    for tool, why in rules.get("retired_tools", {}).items():
        if re.search(r"\b" + re.escape(tool) + r"\b", low):
            msg = f"RETIRED   names {tool!r} ({why})"
            # A page may be about a retirement. Something we send never should be.
            (hard if sending else verify).append(msg)

    if not corpus.strip():
        verify.append("PROOF     no proof files found, so every number in this draft is unverified")
    else:
        known = claim_pairs(corpus)
        seen: set[tuple[str, str]] = set()
        for m in CLAIM.finditer(text):
            pair = as_pair(m.group(0))
            if pair and pair not in seen:
                seen.add(pair)
                if pair not in known:
                    verify.append(f"PROOF     {m.group(0).strip()!r} is not in any proof file. Check it or cut it")
    return hard, verify


def email_checks(text: str, rules: dict) -> tuple[list[str], list[str]]:
    hard: list[str] = []
    verify: list[str] = []
    cfg = rules.get("email", {})
    bangs = text.count("!")
    if bangs > cfg.get("fail_over_exclamations", 2):
        hard.append(f"WARMTH    {bangs} exclamation points. Aim for one, saved for the close or a real win")
    elif bangs > 1:
        verify.append(f"WARMTH    {bangs} exclamation points. Check each one is earned")
    if not re.match(r"^\s*(hey|hi|hello|dear)\b", text, re.I):
        verify.append('OPENING   no greeting line, like "Hi <name>,"')
    if not re.search(r"(?im)^\s*(thanks|thank you|talk soon|best)[!.,]?\s*$", text):
        verify.append("CLOSE     no sign-off line found")
    n = words(text)
    if n > cfg.get("fail_over_words", 200):
        hard.append(f"LENGTH    {n} words. Say what changed, what they need to do, and stop")
    elif n > cfg.get("verify_over_words", 150):
        verify.append(f"LENGTH    {n} words. Check every paragraph is something they need in order to act")
    return hard, verify


def proposal_checks(text: str, rules: dict) -> tuple[list[str], list[str]]:
    hard: list[str] = []
    verify: list[str] = []
    cfg = rules.get("proposal", {})
    lo, hi = cfg.get("min_words", 90), cfg.get("max_words", 160)
    n = words(text)
    if not lo <= n <= hi:
        hard.append(f"LENGTH    {n} words, proposals are {lo} to {hi}")
    for rx in PRICING:
        m = rx.search(text)
        if m:
            hard.append(f"PRICING   {m.group(0)!r}. Pricing comes after a conversation")
            break
    first = re.sub(r"^[^A-Za-z]*", "", text).split(" ")[0].strip(",.:;!?").lower()
    if first == "i":
        hard.append('OPENING   starts with "I". Start with their problem')
    low = text.lower().lstrip()
    for g in GREETINGS:
        if re.match(re.escape(g) + r"\b", low):
            hard.append(f"OPENING   starts with a greeting ({g!r}). Proposals open on the problem")
            break
    sents = sentences(text)
    if not sents:
        hard.append("EMPTY     nothing to check")
    elif not sents[-1].endswith("?"):
        hard.append(f"CLOSE     last sentence is not a question: {sents[-1][:70]!r}")
    return hard, verify


def check(text: str, profile: str, rules: dict, corpus: str) -> tuple[list[str], list[str]]:
    hard, verify = shared_checks(text, profile, rules, corpus)
    if profile == "email":
        h, v = email_checks(text, rules)
    elif profile == "proposal":
        h, v = proposal_checks(text, rules)
    else:
        h, v = [], []
    return hard + h, verify + v


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check a draft against the rules that have one right answer.")
    ap.add_argument("file", help="path to the draft, or - for stdin")
    ap.add_argument("--profile", default="email", choices=PROFILES)
    ap.add_argument("--rules", default=str(DEFAULT_RULES))
    ap.add_argument("--root", default=str(ROOT), help="where proof_files globs are resolved")
    a = ap.parse_args(argv)

    raw = sys.stdin.read() if a.file == "-" else Path(a.file).read_text(encoding="utf-8")
    is_html = a.file != "-" and Path(a.file).suffix.lower() in (".html", ".htm")
    text = strip_html(raw) if is_html else raw
    rules = load_rules(Path(a.rules))
    corpus, read = proof_corpus(Path(a.root), rules)

    hard, verify = check(text, a.profile, rules, corpus)
    print(f"copy_check: {a.profile}, {words(text)} words, proof from {len(read)} file(s)")
    for line in hard:
        print("  FAIL   " + line)
    for line in verify:
        print("  VERIFY " + line)
    if not hard and not verify:
        print("  clean. A reviewer agent still reads it before it goes out.")
    elif not hard:
        print("  no hard failures. Resolve every VERIFY line, then the reviewer agent.")
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
