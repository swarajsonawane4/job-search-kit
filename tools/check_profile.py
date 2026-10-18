#!/usr/bin/env python3
"""Is the profile ready for /hunt? Missing required facts stop a run; the rest only warns.

Usage:  .venv/bin/python tools/check_profile.py

Required, because no application works without them: contact name, email and phone; at
least one language with its level; at least one education entry; and the outreach block
when run.yaml has LinkedIn outreach switched on.

Everything else may stay TODO: an address you have not given, a work-permit sentence, a
salary figure. Forms then leave that field for you and the hand-over lists it.

It also warns when availability was last confirmed long ago. "Available immediately,
20 h/week" written in August goes onto every application in October unless someone
checks it, and a run test in Oct 2026 found exactly that.
"""
import os
import sys
from datetime import date, datetime

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILE = f"{ROOT}/profile/master-profile.yaml"
RUN = f"{ROOT}/run.yaml"
STALE_DAYS = 45

# Example values that mean "not filled in yet".
PLACEHOLDERS = {"firstname lastname", "firstname", "you@example.com", "+49 000 0000000",
                "university name", "m.sc. field", "employer name", "job title"}
PLACEHOLDER_PREFIXES = ("TODO", "One sentence on what you build", "Two sentences on your")


def is_set(value):
    v = " ".join(str(value or "").split())
    return bool(v) and v.lower() not in PLACEHOLDERS and not v.startswith(PLACEHOLDER_PREFIXES)


def todo_paths(node, path=""):
    """Dotted paths of every value still written as TODO."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from todo_paths(v, f"{path}.{k}" if path else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from todo_paths(v, f"{path}[{i}]")
    elif isinstance(node, str) and node.strip().startswith("TODO"):
        yield path


def as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%Y-%m"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def load(path):
    try:
        return yaml.safe_load(open(path, encoding="utf-8")) or {}
    except OSError:
        return None


def main():
    prof = load(PROFILE)
    if prof is None:
        print("  profile/master-profile.yaml is missing. Run: bash setup.sh")
        return 1
    run = load(RUN) or {}

    missing = []
    contact = prof.get("contact") or {}
    for key in ("name", "email", "phone"):
        if not is_set(contact.get(key)):
            missing.append(f"contact.{key}")
    if not any(is_set(l.get("language")) and is_set(l.get("level"))
               for l in prof.get("languages") or []):
        missing.append("languages (at least one, with its level)")
    if not any(is_set(e.get("institution")) and is_set(e.get("degree"))
               for e in prof.get("education") or []):
        missing.append("education (at least one entry)")
    # YAML reads a bare `off` as False, so both spellings mean off.
    mode = (run.get("linkedin") or {}).get("outreach", "off")
    outreach_on = not (mode is False or mode is None
                       or str(mode).strip().lower() in ("off", "false", "no", ""))
    if outreach_on:
        o = prof.get("outreach") or {}
        for key in ("first_name", "school", "one_line", "built"):
            if not is_set(o.get(key)):
                missing.append(f"outreach.{key} (LinkedIn outreach is on in run.yaml)")

    missing_keys = {m.split(" ")[0] for m in missing}

    def covered(p):
        return any(p == k or p.startswith(k + "[") or p.startswith(k + ".") for k in missing_keys)

    optional = [p for p in todo_paths(prof) if not covered(p)]

    print("\n  PROFILE CHECK")
    if missing:
        print(f"  Required, missing ({len(missing)}): a run stops until these are filled")
        for m in missing:
            print(f"    - {m}")
    else:
        print("  Required: all present")
    if optional:
        print(f"  Still TODO ({len(optional)}): fine for a run; forms leave these for you")
        for p in optional[:12]:
            print(f"    - {p}")
        if len(optional) > 12:
            print(f"    ... and {len(optional) - 12} more")

    availability = prof.get("availability") or {}
    confirmed = as_date(availability.get("confirmed"))
    if confirmed is None:
        print("  !! availability.confirmed is not set: add the date you last checked your")
        print("     availability. Until then documents leave availability out.")
    else:
        age = (date.today() - confirmed).days
        if age > STALE_DAYS:
            print(f"  !! availability last confirmed {age} days ago ({confirmed.isoformat()}).")
            print("     Check it: it goes onto every application. Until then documents leave it out.")
    print()
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
