#!/usr/bin/env python3
"""Compile a tailored resume and cover letter, then gate them on what actually
gets applications rejected at first-pass screening.

Usage:  .venv/bin/python tools/apply.py <role_id>
        .venv/bin/python tools/apply.py --all      audit every live role

Expects:
  roles/<role_id>.yaml       role metadata, keyword targets, required documents
  roles/<role_id>.tex        the tailored resume source
  roles/<role_id>.cover.tex  (optional) cover letter source

Writes to out/<role_id>/ and prints a gated report. When every gate passes it also
stages the upload set in out/_upload/<role_id>/: the CV, the cover letter and any
required documents under the names a recruiter will see, plus link-free copies in
no-links/ for portals such as SuccessFactors that reject PDFs with clickable links.
A build that fails any gate clears that folder, so nothing stale is ever uploaded.

Gates, in the order they cost you an application:
  1. Self-negation   — text that hands a screener a reason to reject
  2. Documents       — every attachment the posting demands, staged and ready
  3. Work history    — paid roles silently dropped by a one-page trim
  4. Cross-document  — a cover letter citing a job the CV does not list
  5. JD provenance   — keyword scoring against the real posting, not a memory of it
  6. Length          — one page, always
  7. ATS extraction  — ligature and hyphenation damage
  8. Hidden content  — white text, invisible glyphs, layers, tainted metadata
  9. Transcript      — every course the CV names is actually on the transcript
 10. ATS parser      — contact block, headings, dates, reading order, single column

Reported without gating: hedged skills, em dashes, keyword coverage.
"""
import os
import re
import shutil
import subprocess
import sys
import unicodedata

import yaml
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = shutil.which("pdflatex") or os.path.expanduser("~/Library/TinyTeX/bin/universal-darwin/pdflatex")
UPLOAD = f"{ROOT}/out/_upload"

# Role ids become folder names, and the upload folder is cleared on every build, so
# they are restricted to characters that cannot climb out of out/_upload/.
ROLE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")

# Keys a role YAML may name under required_documents, mapped into docs/.
DOC_STORE = {
    "transcript": "Transcript_of_Records.pdf",
    "enrollment": "Enrollment_Certificate.pdf",
}

# Phrases that argue against the candidate. Three rejections inside 72 hours in
# August 2026 all followed cover letters carrying a dedicated paragraph of these,
# so they are a hard failure rather than a warning.
SELF_NEGATION = [
    r"where I fall short",
    r"what I cannot claim",
    r"I cannot claim",
    r"I fall short",
    r"I have no\b(?! step-by-step)",
    r"I have never\b",
    r"I have not (?:used|worked|done|built)",
    r"no experience (?:with|in|of)",
    r"no exposure",
    r"never (?:worked|operated|used|built)",
    r"\bthose are real gaps\b",
    r"I would be learning",
    r"genuinely new ground",
    r"new ground",
    r"I do not have",
    r"lack(?:ing)? (?:any )?experience",
    r"rather than let you discover",
    r"I would rather (?:say so|set that out|raise)",
    # Availability hedging: the same self-negation in a milder register. Flagging
    # your own start date, hours or duration as a possible obstacle invites the
    # reader to treat it as one. State what you CAN commit to and stop there; if
    # the constraint is real, it belongs in the role YAML and in interview prep.
    r"whether (?:that|this|it) works for you",
    r"overlaps my",
    r"may be an issue",
    r"might be a problem",
    r"if that is (?:a problem|an issue)",
    r"I hope (?:that |this )?is (?:acceptable|alright|not a)",
    r"I understand if",
    r"I realise (?:that )?(?:this|that) (?:is|may|might)",
    r"apolog(?:ise|ize|y)",
    # Disclosing other applications. Caught on 20 Aug 2026 in a real
    # draft. Applying to several roles at a large employer is ordinary and the
    # requisitions sit in separate pipelines; announcing it frames as a problem
    # something the reader was never going to consider.
    r"I am also applying",
    r"I have also applied",
    r"so it is not a surprise",
    r"another (?:role|position|posting) at",
]

# Hedges that read as padding in a keyword list. A screener discounts the whole
# line when one of these appears in it.
RESUME_HEDGES = [
    r"\(familiar\)",
    r"\bfamiliar\b",
    r"working level",
    r"\bconcepts\b",
    r"quick to adopt",
    r"\(shipped\)",
    r"\bbasics\b",
    r"same ecosystem",
    r"\bexposure\b",
]

# Dates a resume parser reads reliably: "Mar 2024", "03/2024", "2024", or an open end.
# German month abbreviations are included for German-language CVs.
MONTH = r"(?:Jan|Feb|M[aä]r|Apr|Ma[iy]|Jun|Jul|Aug|Sep|O[ck]t|Nov|De[cz])[a-zä]*\.?"
DATE_TOKEN = re.compile(
    rf"^(?:{MONTH}\s+\d{{4}}|\d{{1,2}}/\d{{4}}|\d{{4}}|present|current|today|now|heute|laufend)$",
    re.IGNORECASE)
URL = re.compile(r"^(?:https?://)?(?:www\.)?[\w-]+(?:\.[\w-]+)+(?:/\S*)?$", re.IGNORECASE)


# ------------------------------------------------------------------ tex parsing

def tex_body(src):
    """The document body with comments removed: only this part ever renders."""
    s = open(src).read()
    s = s.split(r"\begin{document}")[-1]
    s = s.split(r"\end{document}")[0]
    return re.sub(r"(?<!\\)%.*", "", s)


def brace_span(s, i):
    """(content, index of the closing brace) for the group opening at s[i]."""
    if i >= len(s) or s[i] != "{":
        return None
    depth = 0
    for j in range(i, len(s)):
        if s[j] == "{" and s[j - 1] != "\\":
            depth += 1
        elif s[j] == "}" and s[j - 1] != "\\":
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j
    return None


def macro_args(body, name, n):
    """The first n brace arguments of every use of \\name in the body."""
    found = []
    for m in re.finditer(rf"\\{name}(?![A-Za-z])\*?", body):
        i, args = m.end(), []
        for _ in range(n):
            while i < len(body) and body[i] in " \t\n":
                i += 1
            span = brace_span(body, i)
            if span is None:
                break
            args.append(span[0])
            i = span[1] + 1
        if len(args) == n:
            found.append(args)
    return found


def latex_to_text(s):
    """Approximate the rendered text of a short LaTeX fragment."""
    s = s.replace(r"\&", "&").replace(r"\%", "%").replace(r"\_", "_").replace(r"\#", "#")
    s = re.sub(r"\\textendash(?:\{\})?", "\u2013", s)
    s = re.sub(r"\\textemdash(?:\{\})?", "\u2014", s)
    s = re.sub(r"\\textbar(?:\{\})?", "|", s)
    s = s.replace("---", "\u2014").replace("--", "\u2013")
    s = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", " ", s)
    s = re.sub(r"[{}~]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def canaries_from_source(src):
    """Long words actually present in this .tex — so the check adapts per role.

    A fixed word list gives false failures on tailored resumes, because tailoring
    removes content. Deriving the list from the source tests only what is there.
    """
    s = tex_body(src)
    s = re.sub(r"\\color\{[^}]*\}", " ", s)        # \color{name}: the arg is not text
    s = re.sub(r"\\[a-zA-Z]+\s*", " ", s)          # control sequences
    s = re.sub(r"[{}\[\]$&~^_#]", " ", s)          # markup
    words = re.findall(r"\b[A-Za-z]{8,}\b", s)     # long words break most visibly
    return sorted(set(words))


# ------------------------------------------------------------------ build

def compile_tex(src, outdir):
    os.makedirs(outdir, exist_ok=True)
    pdf = os.path.join(outdir, os.path.basename(src).replace(".tex", ".pdf"))
    if os.path.exists(pdf):
        os.remove(pdf)          # never gate a PDF left over from an earlier build
    for _ in range(2):  # twice, so hyperref/aux settle
        r = subprocess.run(
            [TEX, "-interaction=nonstopmode", f"-output-directory={outdir}", src],
            capture_output=True, text=True, cwd=ROOT)
    if not os.path.exists(pdf):
        sys.exit(f"COMPILE FAILED for {src}\n" + r.stdout[-2500:])
    return pdf


def text_of(pdf):
    raw = " ".join(p.extract_text() or "" for p in PdfReader(pdf).pages)
    return re.sub(r"\s+", " ", raw)


# ------------------------------------------------------------------ gates

def check_extraction(text, src):
    """The ATS-safety gate: catch ligature/kerning/hyphenation damage.

    Two independent signals:
      1. words present in the source that do not survive extraction
      2. defect signatures in the output (mid-word hyphen+space, control chars)
    """
    low = text.lower()
    lost = [w for w in canaries_from_source(src) if w.lower() not in low]
    splits = re.findall(r"\b[a-z]{2,}- [a-z]{2,}\b", text)
    ctrl = re.findall(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", text)
    return lost, splits, ctrl


def find_phrases(text, patterns):
    """Every pattern that matches, with the phrase as it actually appears."""
    found = []
    for p in patterns:
        for m in re.finditer(p, text, re.IGNORECASE):
            found.append((p, m.group(0), excerpt(text, m.start())))
    return found


def excerpt(text, at, width=64):
    lo = max(0, at - width // 3)
    return ("..." if lo else "") + text[lo:at + width].strip() + "..."


def master_experience():
    """Every paid role in the master profile, newest first."""
    prof = yaml.safe_load(open(f"{ROOT}/profile/master-profile.yaml")) or {}
    return [e for e in (prof.get("experience") or []) if e.get("employer")]


def master_employers():
    return [(e["employer"], e.get("dates", "")) for e in master_experience()]


# Leading articles are skipped when picking an employer's distinctive word, or
# "The Example Group" would be matched by every "the" on the page.
ARTICLES = {"the", "der", "die", "das", "le", "la", "les", "el", "il"}


def employer_key(name):
    """The distinctive first word of an employer name; full legal names wrap and
    get shortened on a CV, so matching the whole name gives false failures."""
    words = re.findall(r"[^\s,()]+", name)
    while len(words) > 1 and words[0].lower() in ARTICLES:
        words = words[1:]
    return words[0].lower() if words else ""


def mentions(term, low):
    """Whole-word match, so a short key such as 'ab' does not hit 'about'."""
    return bool(term) and re.search(rf"(?<!\w){re.escape(term)}(?!\w)", low) is not None


def check_work_history(resume_text):
    """A one-page trim must not silently delete paid employment.

    The August 2026 resumes carried one five-month role and dropped eighteen
    months of earlier work, which reads as a gap rather than as brevity.
    """
    low = resume_text.lower()
    return [f"{employer} ({dates})" for employer, dates in master_employers()
            if not mentions(employer_key(employer), low)]


def check_cross_document(resume_text, cover_text):
    """A cover letter must not lean on a job the CV does not list.

    One real cover letter described a year as an R&D intern that appeared nowhere on
    the accompanying CV. A recruiter reading both finds an unbacked claim. Employers
    and job titles both come from the master profile, so this works for any profile.
    """
    if not cover_text:
        return []
    r_low, c_low = resume_text.lower(), cover_text.lower()
    orphans = []
    for e in master_experience():
        employer, dates = e["employer"], e.get("dates", "")
        key = employer_key(employer)
        if mentions(key, c_low) and not mentions(key, r_low):
            orphans.append(f"{employer} ({dates}) — named in cover letter, absent from CV")
        # the same trap without the employer name: a job title carried alone
        title = " ".join(str(e.get("role") or "").split()).lower()
        if len(title) >= 8 and mentions(title, c_low) and not mentions(title, r_low):
            orphans.append(f'"{e.get("role")}" ({employer}) — described in cover letter, absent from CV')
    return orphans


def check_documents(meta):
    """Every attachment the posting demands, staged and ready to upload."""
    required = meta.get("required_documents", [])
    if not required:
        return None, []
    ready, missing = [], []
    for key in required:
        fname = DOC_STORE.get(key)
        if not fname:
            missing.append(f"{key} (no such key in DOC_STORE)")
            continue
        path = f"{ROOT}/docs/{fname}"
        (ready if os.path.exists(path) else missing).append(
            fname if os.path.exists(path) else f"{key} -> docs/{fname} (file not found)")
    return ready, missing


def check_jd(meta):
    """Keyword scoring is only meaningful against the posting's real words."""
    jd = meta.get("jd", "")
    if not jd or not jd.endswith(".md"):
        return f"not saved ({jd or 'unset'}) — keyword targets are unverifiable"
    if not os.path.exists(f"{ROOT}/{jd}"):
        return f"{jd} referenced but missing from disk"
    return None


def check_hidden_content(pdf):
    """Nothing on the page that a reader cannot see but a parser can.

    Checked because the question came up directly whether anything was being embedded.
    Nothing was, and this keeps it that way. Catches the three ways hidden text
    reaches a PDF: painted in white (or near-white) on white, drawn with text
    render mode 3 (invisible), or parked in an optional-content layer.
    """
    problems = []
    reader = PdfReader(pdf)

    for i, page in enumerate(reader.pages, 1):
        try:
            raw = page.get_contents().get_data().decode("latin-1", "replace")
        except Exception:
            continue

        for m in re.finditer(r"([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+rg", raw):
            r, g, b = (float(x) for x in m.groups())
            if min(r, g, b) > 0.90:
                problems.append(f"page {i}: near-white fill colour {r:.2f} {g:.2f} {b:.2f}")

        for m in re.finditer(r"(\d)\s+Tr\b", raw):
            if m.group(1) == "3":
                problems.append(f"page {i}: text render mode 3 (invisible)")

        if "/OC" in raw:
            problems.append(f"page {i}: optional-content (layer) marker")

    props = reader.metadata or {}
    for key, val in props.items():
        if val and re.search(r"claude|anthropic|gpt|openai|generated by|chatgpt|copilot",
                             str(val), re.I):
            problems.append(f"metadata {key}: {val}")

    return sorted(set(problems))


# ------------------------------------------------------------------ ATS parser checks

ATS_SECTIONS = ("EXPERIENCE", "EDUCATION", "SKILLS", "PROJECTS")


def date_parts(d):
    d = re.sub(r"\(.*?\)", " ", d).strip()
    return [p.strip() for p in re.split(r"\s*[-\u2013\u2014]+\s*|\s+to\s+|\s+bis\s+", d)
            if p.strip()]


def is_date_range(d):
    parts = date_parts(d)
    return 0 < len(parts) <= 2 and all(DATE_TOKEN.match(p) for p in parts)


def check_dates(text, src):
    """Every date the CV states, in a format a parser reads, and present in the text.

    Dates come from the second argument of each \\resumeSubheading in the source, so
    a CV with one job is judged on that one job rather than on a fixed count.
    """
    dates = [latex_to_text(a[1]) for a in macro_args(tex_body(src), "resumeSubheading", 2)]
    if not dates:
        found = re.findall(rf"\b{MONTH}\s+\d{{4}}\b|\b\d{{1,2}}/\d{{4}}\b", text, re.IGNORECASE)
        return bool(found), f"dates found in text ({len(found)})", []
    unreadable = [d for d in dates if not is_date_range(d)]
    lost = [d for d in dates if d not in unreadable and not all(p in text for p in date_parts(d))]
    problems = [f'"{d}" unreadable' for d in unreadable] + [f'"{d}" lost in extraction' for d in lost]
    return not problems, f"dates readable ({len(dates)} dated entries)", problems


def check_section_order(text, src):
    """Headings must come out of the PDF in the order the source puts them.

    A parser that reads sections out of order assigns dates and bullets to the wrong
    entry. The expected order is read from the .tex itself, so any section order the
    CV uses is fine as long as extraction preserves it.
    """
    heads = [latex_to_text(a[0]) for a in macro_args(tex_body(src), "section", 1)]
    heads = [h for h in heads if h]
    pos = -1
    for h in heads:
        rendered = h.upper() if h.upper() in text else h   # titlesec upper-cases headings
        at = text.find(rendered, pos + 1)
        if at == -1:
            return False, heads
        pos = at
    return True, heads


def side_by_side_lines(pdf):
    """Lines where two separate runs of prose sit next to each other.

    That is the signature of a two-column or sidebar layout, which a parser reads
    straight across, interleaving both columns. Right-aligned dates and links on an
    entry line are normal and are not counted. Returns None if this pypdf has no
    layout mode.
    """
    def prose(chunk):
        return (not is_date_range(chunk) and not URL.match(chunk)
                and len(re.findall(r"[^\W\d_]{2,}", chunk)) >= 2)

    hits = []
    for page in PdfReader(pdf).pages:
        try:
            layout = page.extract_text(extraction_mode="layout")
        except TypeError:
            return None
        for line in layout.splitlines():
            chunks = [c.strip() for c in re.split(r"\s{6,}", line.strip()) if c.strip()]
            if len(chunks) > 1 and any(prose(c) for c in chunks[1:]):
                hits.append(line.strip())
    return hits


def ats_report(text, pdf, src):
    """Concrete parser checks, not a made-up percentage.

    Everything here is something a resume parser actually does: find the contact
    block, recognise standard section headings, read dates, and get the text out
    in the order a human reads it, one column at a time.
    """
    checks = []
    # Headings render in caps, prose does not, so search the text AS EXTRACTED.
    # Upper-casing everything first made "...MCP experience" in the profile look
    # like the EXPERIENCE heading and broke the reading-order check.
    checks.append(("email found", bool(re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text))))
    checks.append(("phone found", bool(re.search(r"\+\d[\d\s()-]{7,}", text))))

    missing = [h for h in ATS_SECTIONS if h not in text]
    checks.append((f"standard headings ({'/'.join(ATS_SECTIONS).lower()})"
                   + (f": missing {', '.join(missing).lower()}" if missing else ""), not missing))

    ok, label, problems = check_dates(text, src)
    checks.append((label + (f": {'; '.join(problems)}" if problems else ""), ok))

    in_order, heads = check_section_order(text, src)
    checks.append(("reading order matches the source"
                   + ("" if in_order else f" (expected {' > '.join(heads)})"), in_order))

    hits = side_by_side_lines(pdf)
    if hits is None:
        checks.append(("single column: not checked, this pypdf has no layout mode "
                       "(rerun setup.sh)", True))
    else:
        label = f"single column ({len(hits)} lines with text side by side"
        if hits:
            example = re.sub(r"\s{6,}", "  |  ", hits[0])[:80]
            label += f', e.g. "{example}")'
        else:
            label += ")"
        checks.append((label, len(hits) < 3))

    checks.append((f"text layer present ({len(text)} characters extracted)", len(text) > 200))
    return checks


def course_aliases():
    """The profile's course_aliases, lower-cased: the short name a CV uses for a
    course, mapped to its exact titles on the transcript. Kept in the profile, not
    here, so your modules never travel with the shared code."""
    try:
        prof = yaml.safe_load(open(f"{ROOT}/profile/master-profile.yaml")) or {}
    except (OSError, yaml.YAMLError):
        return {}
    table = {}
    for short, titles in (prof.get("course_aliases") or {}).items():
        titles = titles if isinstance(titles, list) else [titles]
        table[str(short).strip().lower()] = [str(t).strip().lower() for t in titles if t]
    return table


def check_transcript_claims(resume_text):
    """Every course named on the CV must appear on the transcript.

    Found on 20 Aug 2026, during a review before sending: all three CVs
    listed "Natural Language Processing" and "Deep Learning for Computer Vision"
    under relevant coursework, and neither module was on the transcript. Harmless
    nowhere, and actively dangerous at an employer that demands
    the transcript and reads it beside the CV.
    """
    m = re.search(r"Relevant coursework:(.*?)(?:\.\s|$)", resume_text, re.S)
    if not m:
        return []                     # no courses named, nothing to verify

    tpath = f"{ROOT}/docs/{DOC_STORE['transcript']}"
    if not os.path.exists(tpath):
        return ["transcript not staged in docs/, so the courses named on the CV cannot be checked"]

    tr = " ".join(p.extract_text() or "" for p in PdfReader(tpath).pages)
    tr = re.sub(r"\s+", " ", tr).lower()

    problems = []
    table = course_aliases()
    for raw in m.group(1).split(","):
        course = raw.strip().rstrip(".").lower()
        if not course or len(course) < 4:
            continue
        aliases = table.get(course)
        if aliases is None:
            # No explicit mapping: fall back to the claim's leading words with any
            # parenthetical dropped, so "Computer Graphics II (Imaging)" still
            # matches the transcript's "Computer Graphics II: Fundamentals of
            # Imaging". Requires at least two words so a single generic term
            # cannot pass by accident.
            stem = re.sub(r"\(.*?\)", " ", course)
            stem = re.sub(r"[^a-z0-9 ]", " ", stem)
            words = [w for w in stem.split() if w]
            aliases = [" ".join(words[:3]), " ".join(words[:2])] if len(words) >= 2 else [course]
        if not any(a in tr for a in aliases):
            problems.append(f'"{raw.strip()}" is not on the transcript')
    return problems


def coverage(text, terms):
    low = text.lower()
    hit, miss = [], []
    for t in terms:
        # a term counts as present if any of its slash-separated aliases appears
        if any(a.strip().lower() in low for a in t.split("/")):
            hit.append(t)
        else:
            miss.append(t)
    return hit, miss


def bar(n, d):
    if not d:
        return ""
    filled = round(20 * n / d)
    return "[" + "#" * filled + "." * (20 - filled) + f"] {n}/{d}"


# ------------------------------------------------------------------ upload staging

def slug(s, limit=40):
    """A filename part every portal accepts: ASCII letters, digits, underscores."""
    s = str(s or "")
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("Ä", "Ae"), ("Ö", "Oe"),
                 ("Ü", "Ue"), ("ß", "ss")):
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")
    return s[:limit].rstrip("_")


def strip_links(src, dst):
    """Copy a PDF without link annotations or document actions.

    SuccessFactors refuses any PDF with "active contents", and hyperref's clickable
    links count. The URLs stay on the page as visible text, so only the click is lost.
    Returns False if the file could not be rewritten (encrypted or signed), in which
    case an untouched copy is written instead.
    """
    try:
        reader = PdfReader(src)
        writer = PdfWriter()
        for page in reader.pages:
            # Drop the annotations before the page is copied, so the link objects
            # never enter the new file at all, not even as unreferenced leftovers
            # that a byte-level scanner would still find.
            if "/Annots" in page:
                del page[NameObject("/Annots")]
            if "/AA" in page:
                del page[NameObject("/AA")]
            writer.add_page(page)
        meta = {k: v for k, v in (reader.metadata or {}).items() if isinstance(v, str)}
        if meta:
            writer.add_metadata(meta)
        with open(dst, "wb") as f:
            writer.write(f)
        return True
    except Exception:
        shutil.copy(src, dst)
        return False


def clear_uploads(rid):
    dest = f"{UPLOAD}/{rid}"
    if os.path.isdir(dest):
        shutil.rmtree(dest)


def stage_uploads(rid, meta, resume_pdf, cover_pdf, docs_ready):
    """Copy a passing build into out/_upload/<rid>/ under recruiter-facing names.

    One folder per role, rebuilt from scratch each time, so a portal never receives
    the previous company's cover letter.
    """
    clear_uploads(rid)
    dest = f"{UPLOAD}/{rid}"
    os.makedirs(f"{dest}/no-links")

    prof = yaml.safe_load(open(f"{ROOT}/profile/master-profile.yaml")) or {}
    person = slug((prof.get("contact") or {}).get("name")) or "Applicant"
    tail = "_".join(p for p in (slug(meta.get("company"), 30), slug(meta.get("role"))) if p)

    files = [(resume_pdf, f"{person}_CV_{tail}.pdf")]
    if cover_pdf:
        files.append((cover_pdf, f"{person}_CoverLetter_{tail}.pdf"))
    for d in docs_ready or []:
        files.append((f"{ROOT}/docs/{d}", f"{person}_{d}"))

    staged, unstripped = [], []
    for src, name in files:
        shutil.copy(src, f"{dest}/{name}")
        if not strip_links(src, f"{dest}/no-links/{name}"):
            unstripped.append(name)
        staged.append(name)
    return staged, unstripped


# ------------------------------------------------------------------ report

def audit(rid, quiet=False):
    """Build and gate one role. Returns True when it is ready to send."""
    meta = yaml.safe_load(open(f"{ROOT}/roles/{rid}.yaml"))

    if meta.get("rejected"):
        clear_uploads(rid)
        if not quiet:
            print(f"\n  REJECTED — {meta['company']}: {meta['role']}")
            print(f"    {meta['rejected']}")
            print("  Do not reapply to this requisition.\n")
        return None

    if meta.get("dropped"):
        clear_uploads(rid)
        if not quiet:
            print(f"\n  DROPPED — {meta['company']}: {meta['role']}")
            print(f"    {meta['dropped']}")
            print("  No documents generated.\n")
        return None

    # Blockers first — a fast "don't bother" beats a beautiful wasted resume.
    if meta.get("blockers"):
        clear_uploads(rid)
        if not quiet:
            print(f"\n  BLOCKED — {meta['company']}: {meta['role']}")
            for b in meta["blockers"]:
                print(f"    - {b}")
            print("  No documents generated.\n")
        return None

    outdir = f"{ROOT}/out/{rid}"
    resume_src = f"{ROOT}/roles/{rid}.tex"
    resume_pdf = compile_tex(f"roles/{rid}.tex", outdir)
    pdfs = [resume_pdf]
    cover_pdf = None
    if os.path.exists(f"{ROOT}/roles/{rid}.cover.tex"):
        cover_pdf = compile_tex(f"roles/{rid}.cover.tex", outdir)
        pdfs.append(cover_pdf)

    pages = len(PdfReader(resume_pdf).pages)
    text = text_of(resume_pdf)
    cover_text = text_of(cover_pdf) if cover_pdf else ""
    lost, splits, ctrl = check_extraction(text, resume_src)

    negations = find_phrases(cover_text, SELF_NEGATION) + find_phrases(text, SELF_NEGATION)
    hedges = find_phrases(text, RESUME_HEDGES)
    dashes = find_phrases(cover_text, [r"\u2014"]) + find_phrases(text, [r"\u2014"])
    missing_jobs = check_work_history(text)
    orphans = check_cross_document(text, cover_text)
    docs_ready, docs_missing = check_documents(meta)
    jd_problem = check_jd(meta)

    print(f"\n  {meta['company']} — {meta['role']}")
    print(f"  {meta.get('location','')}  |  language: {meta.get('language_gate','?')}"
          f"  |  track: {meta.get('track', 'UNSET')}")
    print("  " + "-" * 66)
    for f in meta.get("flags", []):
        print(f"  !! {f}")

    fails = []

    # 1. self-negation
    if negations:
        fails.append("self-negation")
        print(f"  Self-negation  : FAIL — {len(negations)} phrase(s) argue against you")
        for _, phrase, ctx in negations[:6]:
            print(f"    \"{phrase}\"  in: {ctx}")
    else:
        print("  Self-negation  : clean")

    # resume hedges and dashes: reported, not gating
    if hedges:
        print(f"  Hedged skills  : WARN — {len(hedges)}: "
              f"{', '.join(sorted({h[1] for h in hedges}))}")
    else:
        print("  Hedged skills  : clean")
    if dashes:
        print(f"  Dashes         : WARN — {len(dashes)} em dash(es); use a comma, colon or new sentence")
        for _, _, ctx in dashes[:3]:
            print(f"    in: {ctx}")
    else:
        print("  Dashes         : none")

    # 2. documents
    if docs_ready is None:
        print("  Documents      : none required by this posting")
    elif docs_missing:
        fails.append("documents")
        print(f"  Documents      : FAIL — missing {', '.join(docs_missing)}")
    else:
        print(f"  Documents      : ready — {', '.join(docs_ready)}")

    # 3. work history
    if missing_jobs:
        fails.append("work history")
        print(f"  Work history   : FAIL — dropped from CV: {'; '.join(missing_jobs)}")
    else:
        print(f"  Work history   : all {len(master_employers())} paid roles present")

    # 4. cross-document consistency
    if orphans:
        fails.append("cross-document")
        print("  Cross-document : FAIL")
        for o in orphans:
            print(f"    {o}")
    else:
        print("  Cross-document : consistent")

    # 5. JD provenance
    if jd_problem:
        fails.append("jd provenance")
        print(f"  JD source      : FAIL — {jd_problem}")
    else:
        print(f"  JD source      : {meta['jd']}")

    # 6. length
    if pages != 1:
        fails.append("length")
    print(f"  Length         : {'1 page' if pages == 1 else f'FAIL — {pages} pages (one page is mandatory)'}")

    # 7. ATS extraction
    ok = not (lost or splits or ctrl)
    if not ok:
        fails.append("ATS extraction")
    print(f"  ATS extraction : {'clean' if ok else 'FAIL'}")
    if lost:
        print(f"    words lost in extraction : {', '.join(lost[:8])}")
    if splits:
        print(f"    hyphenation splits       : {', '.join(sorted(set(splits))[:8])}")
    if ctrl:
        print(f"    unmapped glyphs          : {len(ctrl)}")

    # 8. nothing hidden on the page
    hidden = check_hidden_content(resume_pdf)
    if cover_pdf:
        hidden += check_hidden_content(cover_pdf)
    if hidden:
        fails.append("hidden content")
        print(f"  Hidden content : FAIL — {len(hidden)} issue(s)")
        for h in hidden:
            print(f"    {h}")
    else:
        print("  Hidden content : none — no white text, no invisible glyphs, no layers")

    # 9. every course the CV names must be on the transcript
    bad_courses = check_transcript_claims(text)
    if bad_courses:
        fails.append("transcript claims")
        print(f"  Transcript     : FAIL — {len(bad_courses)} unverifiable claim(s)")
        for b in bad_courses:
            print(f"    {b}")
    else:
        print("  Transcript     : every course named on the CV appears on it")

    # 10. parser checks
    ats = ats_report(text, resume_pdf, resume_src)
    passed = sum(1 for _, ok in ats if ok)
    if passed < len(ats):
        fails.append("ATS parser checks")
    print(f"  ATS parser     : {passed}/{len(ats)} checks pass")
    for label, ok in ats:
        if not ok:
            print(f"    FAIL  {label}")

    # keyword coverage: reported, not gating
    must = meta.get("must_have", [])
    nice = meta.get("nice_to_have", [])
    mh, mm = coverage(text, must)
    nh, nm = coverage(text, nice)
    print(f"  Must-have      : {bar(len(mh), len(must))}")
    print(f"  Nice-to-have   : {bar(len(nh), len(nice))}")

    if mm:
        print("\n  NOT COVERED (prepare answers for these):")
        for m in mm:
            print(f"    - {m}")
    if nm:
        print(f"  Nice-to-have gaps: {', '.join(nm)}")

    print("\n  Files:")
    for p in pdfs:
        print(f"    {os.path.relpath(p, ROOT)}  ({os.path.getsize(p)//1024} KB)")
    if docs_ready:
        for d in docs_ready:
            print(f"    docs/{d}")

    if fails:
        clear_uploads(rid)
        print(f"\n  NOT READY — {len(fails)} gate(s) failed: {', '.join(fails)}")
        print(f"  Nothing staged in out/_upload/{rid}/ until every gate passes.\n")
        return False

    staged, unstripped = stage_uploads(rid, meta, resume_pdf, cover_pdf, docs_ready)
    print(f"\n  Upload from out/_upload/{rid}/  (SuccessFactors: use the no-links/ copies)")
    for name in staged:
        print(f"    {name}")
    for name in unstripped:
        print(f"    !! {name}: links could not be removed (encrypted or signed PDF); "
              "SuccessFactors may refuse it")
    print("\n  READY TO SEND\n")
    return True


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)

    if sys.argv[1] == "--all":
        results = {}
        for f in sorted(os.listdir(f"{ROOT}/roles")):
            if f.endswith(".yaml") and ROLE_ID.match(f[:-5]):
                results[f[:-5]] = audit(f[:-5])
        live = {k: v for k, v in results.items() if v is not None}
        print("  " + "=" * 66)
        print(f"  {sum(1 for v in live.values() if v)}/{len(live)} live roles ready to send")
        not_ready = [k for k, v in live.items() if not v]
        if not_ready:
            print(f"  Not ready: {', '.join(not_ready)}")
        print()
        return

    rid = sys.argv[1]
    if not ROLE_ID.match(rid):
        sys.exit(f"role_id may only use letters, digits, '.', '_' and '-': {rid!r}")
    audit(rid)


if __name__ == "__main__":
    main()
