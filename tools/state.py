#!/usr/bin/env python3
"""Print the whole pipeline in one screen, so a session can start without reading the corpus.

Usage:  .venv/bin/python tools/state.py

Reads roles/*.yaml and referrals/contacts.yaml and prints current state only: what is
live, what is built and unsent, what came back, what is blocked and why, and who is
mid-conversation. It deliberately prints no history and no lessons — those live in
SWEEP.md and the portal recipes, which are reference material to open when a specific
question arises, not startup reading.
"""
import csv
import os
import re
import sys
from datetime import date, datetime

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROLES = f"{ROOT}/roles"
CONTACTS = f"{ROOT}/referrals/contacts.yaml"
ACCOUNTS = f"{ROOT}/portals/accounts.csv"
# A column name that suggests a secret. accounts.csv is for usernames and login URLs;
# a password in a plain file in this folder ends up in every zip, sync and transcript.
SECRET_COLUMN = re.compile(r"pass|pwd|secret|token|otp|2fa|pin$", re.IGNORECASE)
PROFILE = f"{ROOT}/profile/master-profile.yaml"


def enrollment_valid_until():
    """enrollment_valid_until from the profile, or None. The tracker counts down to it."""
    try:
        v = (yaml.safe_load(open(PROFILE)) or {}).get("enrollment_valid_until")
    except (OSError, yaml.YAMLError):
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v).strip())
    except ValueError:
        return None


def short(text, n=110):
    if not text:
        return ""
    t = " ".join(str(text).split())
    return t if len(t) <= n else t[: n - 1] + "…"


def load_roles():
    out = []
    for f in sorted(os.listdir(ROLES)):
        if not f.endswith(".yaml"):
            continue
        try:
            d = yaml.safe_load(open(f"{ROLES}/{f}")) or {}
        except yaml.YAMLError as e:
            print(f"  !! {f} does not parse: {e}")
            continue
        d["_id"] = f[:-5]
        # apply.py stages out/_upload/<id>/ only when every gate passes
        d["_built"] = os.path.isdir(f"{ROOT}/out/_upload/{d['_id']}")
        out.append(d)
    return out


def bucket(r):
    if r.get("accepted"):
        return "accepted"
    if r.get("rejected"):
        return "rejected"
    if r.get("submitted"):            # a date, or simply true
        return "live"
    if r.get("dropped"):
        return "dropped"
    if r.get("on_hold"):
        return "on_hold"
    if r.get("blockers"):
        return "blocked"
    if r.get("filled"):
        return "filled"
    return "ready" if r["_built"] else "draft"


def check_accounts():
    """Warn loudly if portals/accounts.csv has grown a column for secrets."""
    try:
        with open(ACCOUNTS, newline="") as f:
            header = next(csv.reader(f), [])
    except OSError:
        return
    bad = [h for h in header if SECRET_COLUMN.search(h.strip())]
    if bad:
        print(f"  !! portals/accounts.csv has a '{', '.join(bad)}' column. Delete that column now:")
        print("     passwords and codes belong in your password manager, never in this folder.\n")


def main():
    roles = load_roles()
    by = {}
    for r in roles:
        by.setdefault(bucket(r), []).append(r)

    print(f"\n  PIPELINE — {date.today().isoformat()}")
    print("  " + "-" * 76)
    counts = ", ".join(f"{k} {len(v)}" for k, v in sorted(by.items()))
    print(f"  {counts}\n")
    check_accounts()

    def section(key, title, note=None):
        rows = by.get(key, [])
        if not rows:
            return
        print(f"  {title}")
        if note:
            print(f"    ({note})")
        for r in sorted(rows, key=lambda x: str(x.get("submitted") or x["_id"]), reverse=True):
            when = r.get("submitted") if key in ("accepted", "live", "rejected") else ""
            if key == "filled":
                when = r.get("filled")
            when = "submitted" if when is True else str(when or "").split("#")[0].strip()[:16]
            print(f"    {r['_id']:<20} {short(r.get('company'), 34):<36} {when}")
            if key == "filled":
                portal = r.get("portal") if r.get("portal") not in (None, "TODO") else "portal"
                print(f"      {portal}: {short(r.get('apply_url'), 90)}")
                for item in r.get("left_for_you") or ["nothing left but Submit"]:
                    print(f"      - {short(item, 96)}")
            detail = r.get("accepted") or r.get("rejected") or r.get("on_hold") or r.get("dropped")
            if key in ("accepted", "rejected", "on_hold"):
                print(f"      {short(detail, 100)}")
            if key == "blocked":
                for b in r.get("blockers", [])[:1]:
                    print(f"      {short(b, 100)}")
        print()

    section("accepted", "ACCEPTED")
    section("filled", "FILLED IN CHROME, WAITING FOR YOUR SUBMIT",
            "tab left open; finish what is listed, press Submit, then say: submitted <role_id>")
    section("live", "AWAITING A REPLY")
    section("ready", "READY AND NOT SENT", "passed every gate; re-verify the posting is alive before sending")
    section("on_hold", "ON HOLD — your call")
    section("blocked", "BLOCKED")
    section("rejected", "REJECTED")

    if by.get("draft"):
        print("  IN PROGRESS (no passing build yet)")
        print("    " + ", ".join(r["_id"] for r in by["draft"]) + "\n")
    if by.get("dropped"):
        print("  DROPPED")
        print("    " + ", ".join(r["_id"] for r in by["dropped"]) + "\n")

    # Outreach
    try:
        cs = (yaml.safe_load(open(CONTACTS)) or {}).get("contacts", [])
    except (OSError, yaml.YAMLError):
        cs = []
    if cs:
        waiting = [c for c in cs if c.get("stage") not in ("closed", "blocked")]
        print(f"  OUTREACH — {len(cs)} contacts   (what to send next: tools/referral.py due)")
        for c in sorted(waiting, key=lambda c: c.get("stage", "")):
            last = (c.get("log") or [{}])[-1]
            print(f"    {c['id']:<20} {c.get('stage',''):<9} {c.get('last_reply_sentiment','none'):<8} "
                  f"{short(c.get('name'), 26):<28} last: {last.get('date','—')} {short(last.get('action'), 34)}")
        print()

    # Time bombs
    valid_until = enrollment_valid_until()
    if valid_until:
        days = (valid_until - date.today()).days
        flag = "!!" if days < 30 else "  "
        print(f"  {flag} Enrollment certificate valid {days} more days "
              f"(until {valid_until.isoformat()}).")
        print("     Replace it in docs/ when the new semester's certificate is issued; keep the filename.\n")

    print("  Reference, open only when the question arises:")
    print("    /hunt ................... the whole run: .claude/skills/hunt/SKILL.md, settings in run.yaml")
    print("    runs/<date-time>/log.md . what each run found, filled and sent")
    print("    SWEEP.md ................ sources, and the rules that decide an application")
    print("    portals/<ats>.md ........ quirks of Workday / SuccessFactors / Personio")
    print("    referrals/README.md ..... the five outreach stages and why nobody is asked cold")
    print("    tracks/README.md ........ which base resume suits which posting")
    print("    profile/master-profile.yaml  every answer a form asks for (check it: tools/check_profile.py)\n")


if __name__ == "__main__":
    sys.exit(main())
