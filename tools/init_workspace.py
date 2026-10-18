#!/usr/bin/env python3
"""Create your personal files from the kit's shared examples. Never overwrites.

Usage:  python3 tools/init_workspace.py        (setup.sh runs it for you)

The kit is shared through git with *.example files only. Your own copies, which hold
your details, are made here once and are listed in .gitignore, so they never leave your
machine with a push. Running this again only fills in what is missing.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from newrole import TRACKS                      # one list of track names, kept there

COPIES = [
    ("profile/master-profile.example.yaml", "profile/master-profile.yaml"),
    ("run.example.yaml", "run.yaml"),
    ("portals/accounts.example.csv", "portals/accounts.csv"),
    ("referrals/contacts.example.yaml", "referrals/contacts.yaml"),
]
FOLDERS = ["roles", "jds", "out/_upload", "docs", "tracks", "referrals", "runs"]
TRACK_NOTE = ("% BASE TRACK: {name}. Placeholder until Claude builds it from "
              "profile/master-profile.yaml (see CLAUDE.md, first session).\n")


def main():
    made, kept = [], []
    for folder in FOLDERS:
        os.makedirs(os.path.join(ROOT, folder), exist_ok=True)

    for src, dst in COPIES:
        target = os.path.join(ROOT, dst)
        if os.path.exists(target):
            kept.append(dst)
            continue
        with open(os.path.join(ROOT, src), encoding="utf-8") as f:
            text = f.read()
        with open(target, "w", encoding="utf-8") as f:
            f.write(text)
        made.append(dst)

    with open(os.path.join(ROOT, "template/cv_template.tex"), encoding="utf-8") as f:
        template = f.read()
    for name in TRACKS:
        dst = f"tracks/{name}.tex"
        target = os.path.join(ROOT, dst)
        if os.path.exists(target):
            kept.append(dst)
            continue
        with open(target, "w", encoding="utf-8") as f:
            f.write(TRACK_NOTE.format(name=name) + template)
        made.append(dst)

    for p in made:
        print(f"  created  {p}")
    for p in kept:
        print(f"  kept     {p}  (already yours, left untouched)")
    print("  These files are personal and git-ignored. Share the kit with: git push")
    print("  (check first: .venv/bin/python tools/check_share.py)")


if __name__ == "__main__":
    main()
