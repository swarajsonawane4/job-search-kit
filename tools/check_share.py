#!/usr/bin/env python3
"""Check that nothing personal leaves this folder through git.

Usage:  .venv/bin/python tools/check_share.py

Run it before every git push. It reads every file git tracks or has staged, and fails
when:
  - a personal file is tracked: your profile, run.yaml, portal accounts, LinkedIn
    contacts, base CVs, documents, roles, saved postings, builds or run logs. That
    happens when a file was committed before .gitignore existed, or added with -f;
  - a shared file mentions one of your details: the name, email, phone, street,
    LinkedIn or GitHub handle in your profile, a username in portals/accounts.csv,
    or the name of anyone in referrals/contacts.yaml;
  - a PDF is tracked anywhere. The kit ships none; any PDF is one of yours.

It only reads. How to fix what it finds: START_HERE.md, "Sharing the kit".
"""
import csv
import fnmatch
import os
import re
import subprocess
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Mirrors .gitignore: the files that hold your details.
PERSONAL = [
    "profile/master-profile.yaml", "run.yaml", "portals/accounts.csv",
    "referrals/contacts.yaml", "tracks/*.tex", "docs/*", "roles/*", "jds/*", "out/*",
    "runs/*", "prep/*", ".claude/settings.local.json", ".venv/*",
]
SHARED_EXCEPTIONS = ["docs/README.md", "roles/.keep", "jds/.keep", "out/_upload/.keep",
                     "runs/.keep", "prep/.keep"]

# Values that ship in the examples and mean "not filled in yet".
PLACEHOLDERS = {"", "todo", "firstname lastname", "firstname", "lastname",
                "you@example.com", "your-handle", "+49 000 0000000", "city, country",
                "university name", "employer name"}


def git(*args):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return r.returncode, r.stdout


def is_personal(path):
    if path in SHARED_EXCEPTIONS:
        return False
    return any(fnmatch.fnmatch(path, pat) for pat in PERSONAL)


def load_yaml(rel):
    try:
        return yaml.safe_load(open(os.path.join(ROOT, rel), encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}


def real(value):
    """The value, or "" when it is still the example's placeholder."""
    v = " ".join(str(value or "").split())
    return "" if v.lower() in PLACEHOLDERS or v.startswith("TODO") else v


def needles():
    """(label, text) pairs to look for, and the phone number as bare digits."""
    found, phone = [], ""
    contact = (load_yaml("profile/master-profile.yaml").get("contact") or {})

    name = real(contact.get("name"))
    if name:
        found.append(("your name", name))
        last = name.split()[-1]
        if len(last) >= 7 and last != name:      # long enough to be distinctive
            found.append(("your last name", last))
    email = real(contact.get("email"))
    if email:
        found.append(("your email", email))
    street = real((contact.get("address") or {}).get("street"))
    if street:
        found.append(("your street", street))
    for key, marker in (("linkedin", "/in/"), ("github", "github.com/")):
        url = real(contact.get(key))
        handle = url.split(marker, 1)[-1].strip("/") if marker in url else ""
        if handle and handle.lower() != "your-handle":
            found.append((f"your {key} handle", handle))
    digits = re.sub(r"\D", "", str(contact.get("phone") or ""))
    if len(digits) >= 8 and set(digits[2:]) != {"0"}:
        phone = digits

    try:
        with open(os.path.join(ROOT, "portals/accounts.csv"), newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                user = real(row.get("username"))
                if user:
                    found.append(("a portal username", user))
    except OSError:
        pass

    for c in (load_yaml("referrals/contacts.yaml").get("contacts") or []):
        person = real(c.get("name"))
        if person:
            found.append(("a contact's name", person))
    patterns = [(label, re.compile(r"(?<!\w)" + re.escape(value) + r"(?!\w)", re.IGNORECASE))
                for label, value in found]
    return patterns, phone


def scan(path, needle_list, phone):
    try:
        raw = open(os.path.join(ROOT, path), "rb").read()
    except OSError:
        return []                      # staged for deletion
    if b"\0" in raw[:4096]:
        return []
    text = raw.decode("utf-8", "replace")
    hits = []
    for n, line in enumerate(text.splitlines(), 1):
        for label, pattern in needle_list:
            if pattern.search(line):
                hits.append(f"{path}:{n}: {label}")
        if phone and phone in re.sub(r"\D", "", line):
            hits.append(f"{path}:{n}: your phone number")
    return hits


def main():
    code, _ = git("rev-parse", "--is-inside-work-tree")
    if code != 0:
        print("  Not a git repository, so nothing will be pushed from here.")
        print("  To share the kit as a zip, make it from git so only shared files go in:")
        print("    git init && git add -A && git commit -m kit && git archive -o ../kit.zip HEAD")
        return 0

    _, out = git("ls-files", "-z")
    tracked = [p for p in out.split("\0") if p]
    needle_list, phone = needles()

    problems = []
    for p in tracked:
        if is_personal(p):
            problems.append(f"{p}: personal file is tracked. Run: git rm --cached \"{p}\"")
        elif p.lower().endswith(".pdf"):
            problems.append(f"{p}: a PDF is tracked; the kit ships none. Run: git rm --cached \"{p}\"")
        else:
            problems += scan(p, needle_list, phone)

    if not needle_list and not phone:
        print("  Note: your profile is not filled in yet, so only file locations were checked.")
    if problems:
        print(f"\n  NOT SAFE TO PUSH — {len(problems)} finding(s):")
        for p in problems:
            print(f"    {p}")
        print("\n  Fix these, then run this check again. A file that was already pushed is")
        print("  in the repository's history: see START_HERE.md, 'Sharing the kit'.\n")
        return 1
    print(f"  Nothing personal in the {len(tracked)} files git would push.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
