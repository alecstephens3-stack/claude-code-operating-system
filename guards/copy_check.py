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

Profiles (always named: there is no default, because a missing flag once ran a
video description through the proposal rules and failed it for having no
closing question):
  email     short, a greeting, a sign-off, about one exclamation point. Over
            the word limit only with --long "reason", so a long email is a
            decision someone wrote down
  proposal  word range per --type (cold, invited, detailed, screening), no
            pricing, no contact details or booking links, no greeting line,
            does not open with "I", ends on a question
  artifact  an HTML page: tags, scripts and styles are stripped first, then
            only the shared checks run

Links in an email or a page are opened the way the reader will open them: a
link with a full stop glued to the end fails, a link that does not load fails,
and a page whose images do not load fails. --offline skips the network part.

    python3 guards/copy_check.py draft.txt --profile email
    python3 guards/copy_check.py draft.txt --profile email --long "onboarding steps"
    python3 guards/copy_check.py page.html --profile artifact
    cat draft.txt | python3 guards/copy_check.py - --profile proposal --type invited

The rules (banned phrases, retired tools, limits, which files count as proof)
live in copy_rules.json, so the check and the writing rules cannot disagree.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable

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

# Marketplaces ban contact details before a contract. A portfolio link is fine.
CONTACT = (
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "an email address"),
    (re.compile(r"\b(calendly|cal\.com|whatsapp|telegram|skype)\b", re.I), "an off-platform contact or booking link"),
)

URL = re.compile(r"https?://[^\s<>\"']+")
TRAILING = ".,;:!?)"

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

    for pattern, why in rules.get("banned_patterns", {}).items():
        for m in re.finditer(pattern, low):
            hard.append(f"BANNED    contains {m.group(0)!r}: {why}")

    for tool, why in rules.get("discouraged_tools", {}).items():
        if re.search(r"\b" + re.escape(tool) + r"\b", low):
            verify.append(f"TOOL      names {tool!r}: {why}")

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


def email_checks(text: str, rules: dict, long_reason: str | None = None) -> tuple[list[str], list[str]]:
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
    limit = cfg.get("fail_over_words", 100)
    if n > limit and not long_reason:
        hard.append(f"LENGTH    {n} words, the limit is {limit}. Say what changed, what they need to do, "
                    'and stop. If it truly has to be longer, re-run with --long "why"')
    elif n > limit:
        verify.append(f"LENGTH    {n} words, allowed because: {long_reason}. Check that holds for every paragraph")
    elif n > cfg.get("verify_over_words", 70):
        verify.append(f"LENGTH    {n} words. Check every paragraph is something they need in order to act")
    return hard, verify


def proposal_checks(text: str, rules: dict, kind: str = "cold") -> tuple[list[str], list[str]]:
    hard: list[str] = []
    verify: list[str] = []
    types = rules.get("proposal", {}).get("types", {"cold": [100, 150]})
    if kind not in types:
        return [f"TYPE      unknown proposal type {kind!r}, one of {sorted(types)}"], []
    lo, hi = types[kind]
    n = words(text)
    if not lo <= n <= hi:
        hard.append(f"LENGTH    {n} words, {kind} proposals are {lo} to {hi}")
    for rx in PRICING:
        m = rx.search(text)
        if m:
            hard.append(f"PRICING   {m.group(0)!r}. Pricing comes after a conversation")
            break
    for rx, what in CONTACT:
        m = rx.search(text)
        if m:
            hard.append(f"CONTACT   {what}: {m.group(0)!r}. The marketplace bans contact details before a contract")
    # A screening answer may start with "I" and ends on a fact, not a question.
    if kind == "screening":
        return hard, verify
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
    elif " or " not in sents[-1].lower() and not re.match(
            r"^(would|should|does|is|are|can|could|do|did|will|have|has)\b", sents[-1], re.I):
        verify.append(f"CLOSE     the question may be open-ended rather than a yes or no: {sents[-1][:70]!r}")
    return hard, verify


Fetch = Callable[[str], tuple[str, str, bytes]]
Head = Callable[[str], int]
AGENT = {"User-Agent": "Mozilla/5.0 (copy_check link test)"}


def urllib_fetch(url: str) -> tuple[str, str, bytes]:
    with urllib.request.urlopen(urllib.request.Request(url, headers=AGENT), timeout=20) as r:
        return r.geturl(), r.headers.get("Content-Type", ""), r.read(2_000_000)


def urllib_head(url: str) -> int:
    with urllib.request.urlopen(urllib.request.Request(url, method="HEAD", headers=AGENT), timeout=20) as r:
        return r.status


def find_links(text: str, raw_html: str | None = None) -> list[str]:
    """Links in the prose, plus href targets when the draft is a page."""
    links = [m.group(0) for m in URL.finditer(text)]
    if raw_html:
        links += re.findall(r"""href=["'](https?://[^"']+)["']""", raw_html)
    return list(dict.fromkeys(links))


def link_checks(links: list[str], fetch: Fetch | None = None,
                head: Head | None = None) -> tuple[list[str], list[str]]:
    """Open every link the way the reader will. With no fetch, only the offline checks run.

    A mail app glues trailing punctuation onto a link, so "see https://x.co/page." opens
    a page that does not exist. That one is caught without any network.
    """
    hard: list[str] = []
    verify: list[str] = []
    for url in links:
        if url[-1] in TRAILING:
            hard.append(f"LINK      {url!r} ends in {url[-1]!r}, which the mail app makes part of the link. "
                        "Put the link on its own line")
            url = url.rstrip(TRAILING)
        if fetch is None:
            continue
        try:
            final, ctype, body = fetch(url)
        except Exception as e:  # noqa: BLE001 - any failure to open is the finding
            hard.append(f"LINK      {url} does not open: {str(e)[:80]}")
            continue
        if "html" not in ctype or head is None:
            continue
        broken = []
        for src in re.findall(r"""<img[^>]+src=["']([^"']+)""", body.decode("utf-8", "ignore")):
            if src.startswith("data:"):
                continue
            try:
                if head(urllib.parse.urljoin(final, html.unescape(src))) >= 400:
                    broken.append(src)
            except Exception:  # noqa: BLE001
                broken.append(src)
        if broken:
            hard.append(f"LINK      {url} opens but {len(broken)} image(s) do not load, e.g. {broken[0]!r}")
    return hard, verify


def check(text: str, profile: str, rules: dict, corpus: str, kind: str = "cold",
          long_reason: str | None = None) -> tuple[list[str], list[str]]:
    """Everything that needs no network. Links are checked separately in link_checks."""
    hard, verify = shared_checks(text, profile, rules, corpus)
    if profile == "email":
        h, v = email_checks(text, rules, long_reason)
    elif profile == "proposal":
        h, v = proposal_checks(text, rules, kind)
    else:
        h, v = [], []
    return hard + h, verify + v


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check a draft against the rules that have one right answer.")
    ap.add_argument("file", help="path to the draft, or - for stdin")
    ap.add_argument("--profile", required=True, choices=PROFILES,
                    help="the surface: email, proposal, or artifact for everything else that goes out")
    ap.add_argument("--type", default="cold", help="proposal type, from copy_rules.json (default: cold)")
    ap.add_argument("--long", metavar="REASON", help="email only: why this one runs past the word limit")
    ap.add_argument("--offline", action="store_true", help="check links without opening them")
    ap.add_argument("--rules", default=str(DEFAULT_RULES))
    ap.add_argument("--root", default=str(ROOT), help="where proof_files globs are resolved")
    a = ap.parse_args(argv)

    raw = sys.stdin.read() if a.file == "-" else Path(a.file).read_text(encoding="utf-8")
    is_html = a.file != "-" and Path(a.file).suffix.lower() in (".html", ".htm")
    text = strip_html(raw) if is_html else raw
    rules = load_rules(Path(a.rules))
    corpus, read = proof_corpus(Path(a.root), rules)

    hard, verify = check(text, a.profile, rules, corpus, a.type, a.long)
    if a.profile in ("email", "artifact"):
        links = find_links(text, raw if is_html else None)
        lh, lv = link_checks(links, None if a.offline else urllib_fetch, None if a.offline else urllib_head)
        hard, verify = hard + lh, verify + lv
    label = f"proposal/{a.type}" if a.profile == "proposal" else a.profile
    print(f"copy_check: {label}, {words(text)} words, proof from {len(read)} file(s)")
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
