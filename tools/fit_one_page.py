#!/usr/bin/env python3
"""Trim a tailored resume until it fits on one page, protecting what matters.

Usage:  .venv/bin/python tools/fit_one_page.py <role_id> [<role_id> ...]
        .venv/bin/python tools/fit_one_page.py --all

One page is a hard rule, and the honest cost of restoring the full work history
is that some resumes now run over. Trimming by eye is how content that carries a
must-have keyword gets cut by accident, so this does it by rule instead:

  - drops the LAST item from the LONGEST skills line, repeatedly
  - never drops an item that is the only place a must_have or nice_to_have term
    appears, so keyword coverage cannot regress
  - never touches the Languages line, Profile, Projects, Education or Experience
  - stops the moment the PDF is one page, and reports what it removed

If it runs out of droppable items the resume still does not fit, it says so and
changes nothing further. That case needs a human decision about which project or
bullet to cut, which is exactly the decision worth flagging rather than guessing.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

import yaml
from pypdf import PdfReader

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = shutil.which("pdflatex") or os.path.expanduser("~/Library/TinyTeX/bin/universal-darwin/pdflatex")

SKILL_RE = re.compile(r"(\\skillLine\{[^}]*\}\{)(.*)(\}\s*)$")


def split_items(s):
    items, depth, buf = [], 0, ""
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            items.append(buf.strip())
            buf = ""
        else:
            buf += ch
    if buf.strip():
        items.append(buf.strip())
    return [i for i in items if i]


def page_count(tex_path):
    """Compile to a throwaway directory so out/ only ever holds a final build."""
    with tempfile.TemporaryDirectory() as tmp:
        for _ in range(2):
            subprocess.run([TEX, "-interaction=nonstopmode",
                            f"-output-directory={tmp}", tex_path],
                           capture_output=True, text=True, cwd=ROOT)
        pdf = os.path.join(tmp, os.path.basename(tex_path).replace(".tex", ".pdf"))
        if not os.path.exists(pdf):
            return None
        return len(PdfReader(pdf).pages)


def protected_terms(meta):
    terms = list(meta.get("must_have", [])) + list(meta.get("nice_to_have", []))
    out = set()
    for t in terms:
        for alias in t.split("/"):
            alias = alias.strip().lower()
            if alias:
                out.add(alias)
    return out


def body_text(lines):
    return " ".join(lines).lower()


def fit(rid):
    tex_path = f"{ROOT}/roles/{rid}.tex"
    meta = yaml.safe_load(open(f"{ROOT}/roles/{rid}.yaml"))
    if meta.get("dropped") or meta.get("blockers"):
        return None

    pages = page_count(tex_path)
    if pages is None:
        print(f"  {rid}: COMPILE FAILED")
        return False
    if pages == 1:
        print(f"  {rid}: already 1 page")
        return True

    backup = tex_path + ".prefit"
    shutil.copy(tex_path, backup)
    protect = protected_terms(meta)
    removed = []

    while pages != 1:
        lines = open(tex_path).read().split("\n")
        idxs = [i for i, l in enumerate(lines)
                if SKILL_RE.match(l) and "Languages: " not in l]
        if not idxs:
            break

        # longest line first: the biggest saving per item dropped
        idxs.sort(key=lambda i: len(lines[i]), reverse=True)
        dropped_this_round = False

        for i in idxs:
            m = SKILL_RE.match(lines[i])
            items = split_items(m.group(2))
            if len(items) <= 2:
                continue                       # keep every line meaningful
            candidate = items[-1]

            trial = lines[:]
            trial[i] = m.group(1) + ", ".join(items[:-1]) + m.group(3)

            # would this remove the last mention of a targeted keyword?
            rest = body_text(trial)
            cand_low = candidate.lower()
            guarded = [t for t in protect if t in cand_low and t not in rest]
            if guarded:
                # try the next-to-last item instead before giving up on this line
                placed = False
                for j in range(len(items) - 2, 0, -1):
                    alt = items[j].lower()
                    trial2 = lines[:]
                    keep = items[:j] + items[j + 1:]
                    trial2[i] = m.group(1) + ", ".join(keep) + m.group(3)
                    if not [t for t in protect if t in alt and t not in body_text(trial2)]:
                        trial, candidate, placed = trial2, items[j], True
                        break
                if not placed:
                    continue

            open(tex_path, "w").write("\n".join(trial))
            removed.append(candidate)
            dropped_this_round = True
            break

        if not dropped_this_round:
            break
        pages = page_count(tex_path)

    if pages == 1:
        os.remove(backup)
        print(f"  {rid}: fitted to 1 page, dropped {len(removed)} skill item(s)")
        for r in removed:
            print(f"      - {r}")
        return True

    shutil.copy(backup, tex_path)
    os.remove(backup)
    print(f"  {rid}: STILL {pages} PAGES after exhausting safe skill trims.")
    print("      Reverted. Cut a project bullet or an Education line by hand.")
    return False


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if sys.argv[1] == "--all":
        rids = sorted(f[:-5] for f in os.listdir(f"{ROOT}/roles") if f.endswith(".yaml"))
    else:
        rids = sys.argv[1:]
    for rid in rids:
        fit(rid)


if __name__ == "__main__":
    main()
