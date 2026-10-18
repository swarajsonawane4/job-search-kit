#!/usr/bin/env python3
"""Draft, gate and record staged referral outreach on LinkedIn.

Usage:
  .venv/bin/python tools/referral.py list
  .venv/bin/python tools/referral.py due
  .venv/bin/python tools/referral.py draft    <contact_id>
  .venv/bin/python tools/referral.py sent     <contact_id> [--no-note]
  .venv/bin/python tools/referral.py accepted <contact_id>
  .venv/bin/python tools/referral.py reply    <contact_id> <positive|neutral|negative> "their words"

The five stages and the reasoning behind them are in referrals/README.md. The short
version: nobody is asked for a referral cold. A contact advances only when they have
actually responded (accepted the request, or replied), and the stage 5 ask is blocked
unless their last reply read positive and the application has been submitted.

This tool drafts and keeps the record; it never sends. Who presses Send is set in
run.yaml (linkedin.outreach): Claude in your Chrome, or you. Either way, nothing goes
out that failed a gate here, and nothing goes out twice in one stage.
"""
import os
import re
import sys
from datetime import date

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTACTS = f"{ROOT}/referrals/contacts.yaml"
RUN_CONFIG = f"{ROOT}/run.yaml"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apply import SELF_NEGATION, find_phrases          # same linter as the applications

STAGES = ["connect", "opener", "culture", "fit", "ask", "thanks", "closed"]

# LinkedIn's cap on a connection-request note, by account type. Free accounts were
# reported at 200 characters and only a few personalised notes a month (2026);
# Premium at 300. LinkedIn changes these, so the account type lives in run.yaml.
NOTE_LIMITS = {"free": 200, "premium": 300}

# Asking too early is the failure this whole sequence exists to prevent, so the word
# is banned outright before stage 5.
PREMATURE_ASK = [r"\brefer(?:ral|ring|ence)?\b", r"put in a good word", r"vouch for",
                 r"pass (?:my|it) on", r"forward my (?:CV|application|profile)"]


def load():
    data = yaml.safe_load(open(CONTACTS)) or {}
    data.setdefault("contacts", [])
    if data["contacts"] is None:
        data["contacts"] = []
    return data


# yaml.safe_dump silently discards every comment in the file, so the header has to be
# re-emitted on each write. Learned by losing it on 20 Aug 2026. Anything that must
# survive a save belongs in a YAML field (why/notes), not in a comment.
HEADER = """# Referral outreach tracker. Stages and rules: referrals/README.md
# Drive it with tools/referral.py: it drafts, gates and records. It never sends.
# Who presses Send is set in run.yaml (linkedin.outreach): send, type or off.
#
# route: hiring_team | alumni | peer | recruiter
# stage: connect -> opener -> culture -> fit -> ask -> thanks -> closed
# last_reply_sentiment: none | neutral | positive | negative
#   The stage 5 ask stays blocked until this reads 'positive' and the application
#   has been submitted.
#
# Contacts come from LinkedIn profiles, found by you or by /hunt in your Chrome.
# Record only what LinkedIn shows publicly for professional contact: name, headline,
# employer, profile URL, and the checkable reason for reaching out. Nothing else.
#
# Finding people: the company People tab works where a job page's "recent hires" panel
# does not, e.g. /company/<slug>/people/?keywords=working+student

"""


def save(data):
    with open(CONTACTS, "w") as f:
        f.write(HEADER)
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True, width=88)


def get(data, cid):
    for c in data["contacts"]:
        if c["id"] == cid:
            return c
    sys.exit(f"no contact '{cid}'. Try: tools/referral.py list")


def role_meta(c):
    p = f"{ROOT}/roles/{c.get('role')}.yaml"
    return (yaml.safe_load(open(p)) or {}) if os.path.exists(p) else {}


def run_config():
    try:
        return yaml.safe_load(open(RUN_CONFIG)) or {}
    except (OSError, yaml.YAMLError):
        return {}


def outreach_mode():
    """send | type | off, from run.yaml linkedin.outreach. Missing means type."""
    v = (run_config().get("linkedin") or {}).get("outreach", "type")
    # YAML reads a bare `off` as the boolean False (and `on` as True), so map those back.
    if v is False:
        return "off"
    if v is None or v is True:
        return "type"
    return str(v).strip().lower()


def blocked_reason(c, r):
    """Why nothing may be drafted or recorded for this contact now, or None."""
    stage = c["stage"]
    if outreach_mode() == "off":
        return ("outreach is off in run.yaml (linkedin.outreach: off). "
                "Nothing is drafted or recorded while it is off.")
    if stage == "ask" and c.get("last_reply_sentiment") != "positive":
        return (f"last reply reads '{c.get('last_reply_sentiment', 'none')}', not 'positive'. "
                "Ask only if the conversation turned out positive; stay at 'fit' or close with 'thanks'.")
    if stage == "ask" and not submitted(r):
        return (f"the application for {r.get('role', c.get('role'))} is not submitted. "
                "Submit it, record submitted: in its role YAML, then draft the ask.")
    return None


def current_draft(c, r):
    """The text for the contact's current stage and the gate results for it."""
    stage = c["stage"]
    text = c.get(f"custom_{stage}") or TEMPLATES[stage](c, r)
    problems, warnings = gate(text, stage, c)
    return text, problems, warnings


def note_limit():
    account = str((run_config().get("linkedin") or {}).get("account") or "free").lower()
    return NOTE_LIMITS.get(account, NOTE_LIMITS["free"])


def last_entry(c):
    log = c.get("log") or []
    return log[-1] if log else {}


def awaiting(c):
    """The current stage was sent and nothing has come back since."""
    last = last_entry(c)
    return last.get("action") == "sent" and last.get("stage") == c["stage"]


def submitted(r):
    return bool(r.get("submitted"))


# --------------------------------------------------------------------- templates
#
# Written to be edited. The tool fills the slots and checks the result; it does not
# pretend the generated wording is final. A contact's custom_<stage> field, when set,
# replaces the template for that stage.

def me():
    """Your pitch, from the outreach block of profile/master-profile.yaml."""
    prof = yaml.safe_load(open(f"{ROOT}/profile/master-profile.yaml")) or {}
    o = prof.get("outreach") or {}
    missing = [k for k in ("first_name", "school", "one_line", "built") if not o.get(k)]
    if missing:
        sys.exit(f"fill outreach: {', '.join(missing)} in profile/master-profile.yaml first")
    return o


def t_connect(c, r):
    """Stage 1. Warm, first-person, no ask. 'Just applied' only once it is true:
    /hunt reaches people while the application still waits for your Submit."""
    o = me()
    role = r.get("role", "a role on your team")
    company = r.get("company", c["employer"])
    if submitted(r):
        doing, doing_at = f"and just applied for {role}.", f"Just applied to {company}."
    else:
        doing, doing_at = f"and I'm applying for {role}.", f"I'm applying to {company}."
    return {
        "hiring_team": (
            f"Hi {c['first']}, I'm {o['first_name']}, a student at {o['school']}, {doing} "
            f"{o['one_line']} Would be great to connect."),
        "alumni": (
            f"Hi {c['first']}, I'm {o['first_name']}, studying at {o['school']} like you did. "
            f"{o['one_line']} {doing_at} Would love to connect."),
        "peer": (
            f"Hi {c['first']}, I'm {o['first_name']}, a student at {o['school']}. "
            f"{o['one_line']} {doing_at} Would love to hear how you find it there."),
        "recruiter": (
            f"Hi {c['first']}, I'm {o['first_name']}, a student at {o['school']}, {doing} "
            f"{o['one_line']} Would be great to connect."),
    }[c["route"]]


def t_opener(c, r):
    """Stage 2. Two lines on what you build, then a question with an easy out. The
    double ask ("or if you're too busy...") makes saying yes to something easier
    than saying no to everything."""
    o = me()
    return (
        f"Thanks for connecting, {c['first']}!\n\n"
        f"Quick bit about me: {o['built']}\n\n"
        f"I'd love to hear about your experience at {c['employer']} and what the team "
        f"is really working on. Would you be open to a quick chat? And if you're too "
        f"busy for that, even a couple of lines would be great.")


def t_culture(c, r):
    """Stage 3. The real questions. Their answers shape stage 4, so these have to be
    things you actually want to know."""
    return (
        f"Thanks {c['first']}, that's really useful.\n\n"
        f"Two things I'd genuinely like to know before I get further into this.\n\n"
        f"What does a normal week look like there, and how much of it is hands-on "
        f"building versus everything around it?\n\n"
        f"And if someone joined and did well, what would they have gotten right in "
        f"the first six months?\n\n"
        f"No rush at all, whenever you have a minute.")


def t_fit(c, r):
    """Stage 4. Deliberately NOT pre-written. This message has to answer what they
    actually said, in their words. A generic version reads as a pitch and undoes the
    goodwill the first three stages earned. The gate fails while a [SLOT] remains, so
    this stage only goes out once custom_fit holds the real message."""
    return (
        f"That lines up with what I've been doing, so let me be specific.\n\n"
        f"[ANSWER WHAT THEY ACTUALLY SAID, USING THEIR WORDS. Pick the ONE project or "
        f"job from master-profile.yaml that maps to what they described. Not all of them.]\n\n"
        f"[CLOSE WITH A QUESTION, not a summary of yourself.]")


def t_ask(c, r):
    """Stage 5. Only reachable on a positive reply and a submitted application.
    Easy to decline by design."""
    when = r.get("submitted")
    when = f" on {when}" if when and when is not True else ""
    req = f" (req {c['req']})" if c.get("req") else ""
    return (
        f"Thanks {c['first']}, this has been genuinely helpful.\n\n"
        f"One thing I wanted to ask, and please just say no if it's awkward. My "
        f"application for {r.get('role', 'the role')}{req} went in{when}. From what "
        f"we've talked about, if you think I'd fit the team, would you be comfortable "
        f"flagging it internally?\n\n"
        f"Either way, I really appreciate the time you've taken.")


def t_thanks(c, r):
    return (f"Thanks {c['first']}, I appreciate you taking the time. I'll let you know "
            f"how it goes, and good luck with everything at {c['employer']}.")


TEMPLATES = {"connect": t_connect, "opener": t_opener, "culture": t_culture,
             "fit": t_fit, "ask": t_ask, "thanks": t_thanks}


# ------------------------------------------------------------------------- gates

def gate(text, stage, contact):
    problems, warnings = [], []

    limit = note_limit()
    if stage == "connect" and len(text) > limit:
        problems.append(f"connection note is {len(text)} chars; your LinkedIn account "
                        f"(run.yaml linkedin.account) takes {limit}. Write a shorter "
                        f"custom_connect")

    for _, phrase, ctx in find_phrases(text, SELF_NEGATION):
        problems.append(f'self-negation: "{phrase}" in: {ctx}')

    if stage != "ask":
        for pat in PREMATURE_ASK:
            m = re.search(pat, text, re.I)
            if m:
                problems.append(f'asks too early: "{m.group(0)}" at stage {stage}. '
                                f'The ask belongs in stage 5 and nowhere before it.')

    if re.search(r"\[[A-Z][^\]]*\]", text):
        problems.append("contains a [SLOT]: write this stage's custom field with the real "
                        f"message (custom_{stage} in contacts.yaml)")

    if "—" in text:
        warnings.append("em dash: use a comma, a colon or a separate sentence")

    return problems, warnings


# ---------------------------------------------------------------------- commands

def cmd_list(data):
    print()
    print(f"  {'id':16s} {'stage':9s} {'reply':9s} {'route':11s} contact")
    print("  " + "-" * 78)
    for c in data["contacts"]:
        print(f"  {c['id']:16s} {c['stage']:9s} "
              f"{c.get('last_reply_sentiment','none'):9s} {c['route']:11s} "
              f"{c['name']} · {c['employer']}")
    print()


def cmd_due(data):
    """What outreach needs doing, most actionable first."""
    send, waiting, blocked = [], [], []
    today = date.today()
    for c in data["contacts"]:
        if c["stage"] == "closed":
            continue
        r = role_meta(c)
        if awaiting(c):
            when = str(last_entry(c).get("date", ""))
            try:
                days = (today - date.fromisoformat(when)).days
            except ValueError:
                days = None
            note = f"{days} days" if days is not None else "since ?"
            if days is not None and days >= 14:
                note += ", consider closing with thanks"
            waiting.append((c, f"sent {c['stage']} on {when} ({note})"))
        elif c["stage"] == "ask" and c.get("last_reply_sentiment") != "positive":
            blocked.append((c, "ask blocked: last reply not positive; stay at fit or send thanks"))
        elif c["stage"] == "ask" and not submitted(r):
            blocked.append((c, "ask blocked: application not submitted yet"))
        else:
            send.append((c, f"send {c['stage']}"))

    print()
    for title, rows in (("TO SEND", send), ("BLOCKED", blocked), ("WAITING FOR THEM", waiting)):
        if not rows:
            continue
        print(f"  {title}")
        for c, what in rows:
            print(f"    {c['id']:18s} {c['name'][:24]:24s} {c['employer'][:22]:22s} {what}")
        print()
    if not (send or blocked or waiting):
        print("  Nothing due.\n")


def cmd_draft(data, cid):
    c = get(data, cid)
    r = role_meta(c)
    stage = c["stage"]

    if stage == "closed":
        sys.exit(f"  {cid} is closed.")

    if awaiting(c):
        last = last_entry(c)
        print(f"\n  WAITING — '{stage}' already went to {c['name']} on {last.get('date')}.")
        print("  Nothing to send until they accept or reply:")
        print(f"    tools/referral.py accepted {cid}      (connection accepted)")
        print(f"    tools/referral.py reply {cid} <positive|neutral|negative> \"...\"\n")
        return

    reason = blocked_reason(c, r)
    if reason:
        print(f"\n  BLOCKED — nothing to draft for {cid}.")
        print(f"    {reason}\n")
        sys.exit(1)

    text, problems, warnings = current_draft(c, r)

    n = STAGES.index(stage) + 1
    where = f"stage {n}/5: {stage}" if n <= 5 else f"after the ask: {stage}"
    print(f"\n  {c['name']} · {c['employer']} · {c['route']}")
    print(f"  {where}   |   {c.get('linkedin','')}")
    print("  " + "=" * 78)
    print()
    for line in text.split("\n"):
        print(f"  {line}")
    print()
    print("  " + "-" * 78)
    print(f"  {len(text)} chars"
          + (f"  (limit {note_limit()})" if stage == "connect" else ""))
    for w in warnings:
        print(f"  WARN  {w}")
    for p in problems:
        print(f"  FAIL  {p}")
    if problems:
        print("\n  NOT READY — fix the above. Nothing may be sent.\n")
        sys.exit(1)
    else:
        print("\n  READY — send exactly this (run.yaml linkedin.outreach decides who presses Send)")
        print(f"  After it is sent:  tools/referral.py sent {cid}"
              + ("   (add --no-note if LinkedIn took the request without the note)"
                 if stage == "connect" else ""))
    print()


def cmd_sent(data, cid, no_note=False):
    c = get(data, cid)
    if c["stage"] == "closed":
        sys.exit(f"  {cid} is closed.")
    if awaiting(c):
        sys.exit(f"  {cid}: '{c['stage']}' is already recorded as sent on "
                 f"{last_entry(c).get('date')}. Not recording it twice.")
    r = role_meta(c)
    reason = blocked_reason(c, r)
    if reason:
        sys.exit(f"  {cid}: not recorded. {reason}")
    if not no_note:
        # What went out must be what passed the gates; refuse to record a failed draft.
        _, problems, _ = current_draft(c, r)
        if problems:
            sys.exit(f"  {cid}: not recorded. The current '{c['stage']}' draft fails its gates "
                     f"({'; '.join(problems)}). Fix it with tools/referral.py draft {cid} first.")
    entry = {"date": str(date.today()), "stage": c["stage"], "action": "sent"}
    if no_note:
        if c["stage"] != "connect":
            sys.exit("  --no-note only applies to a connection request")
        entry["note"] = False
    c.setdefault("log", []).append(entry)
    if c["stage"] == "thanks":
        c["stage"] = "closed"
        print(f"  {cid}: thanks sent. Closed.")
    else:
        print(f"  {cid}: recorded '{c['stage']}' as sent"
              + (" without a note" if no_note else "") + ". Waiting on them.")
        print(f"  When they accept:  tools/referral.py accepted {cid}")
        print(f"  When they answer:  tools/referral.py reply {cid} <positive|neutral|negative> \"...\"")
    save(data)


def cmd_accepted(data, cid):
    """A connection request was accepted. That is a response, so stage 2 is due."""
    c = get(data, cid)
    if c["stage"] != "connect":
        sys.exit(f"  {cid} is at stage '{c['stage']}', not 'connect'. Use reply for a message.")
    c.setdefault("log", []).append(
        {"date": str(date.today()), "stage": "connect", "action": "accepted"})
    c["stage"] = "opener"
    print(f"  {cid}: connection accepted. Stage 2 (opener) is due: tools/referral.py draft {cid}")
    save(data)


def cmd_reply(data, cid, sentiment, text):
    if sentiment not in ("positive", "neutral", "negative"):
        sys.exit("sentiment must be positive, neutral or negative")
    c = get(data, cid)
    if c["stage"] == "closed":
        sys.exit(f"  {cid} is closed.")
    c["last_reply_sentiment"] = sentiment
    c.setdefault("log", []).append(
        {"date": str(date.today()), "stage": c["stage"], "action": "reply",
         "sentiment": sentiment, "text": text[:400]})

    if sentiment == "negative":
        c["stage"] = "thanks"
        print(f"  {cid}: negative reply recorded. Moved to 'thanks'. Close it gracefully;")
        print("  a contact who says no this time is still a contact.")
    else:
        i = STAGES.index(c["stage"])
        c["stage"] = STAGES[min(i + 1, len(STAGES) - 1)]
        print(f"  {cid}: reply recorded as {sentiment}. Now at stage '{c['stage']}'.")
        if c["stage"] == "ask" and sentiment != "positive":
            print("  NOTE: the ask will stay blocked until a reply reads 'positive'.")
    save(data)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    data = load()
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "list":
        cmd_list(data)
    elif cmd == "due":
        cmd_due(data)
    elif cmd == "draft" and len(args) == 1:
        cmd_draft(data, args[0])
    elif cmd == "sent" and len(args) in (1, 2) and (len(args) == 1 or args[1] == "--no-note"):
        cmd_sent(data, args[0], no_note=len(args) == 2)
    elif cmd == "accepted" and len(args) == 1:
        cmd_accepted(data, args[0])
    elif cmd == "reply" and len(args) >= 2:
        cmd_reply(data, args[0], args[1], " ".join(args[2:]))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
