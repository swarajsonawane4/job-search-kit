#!/usr/bin/env python3
"""Scaffold a new role from the right track.

Usage:  .venv/bin/python tools/newrole.py <role_id> <track> "<Company>" "<Role title>"

        track is one of the names in TRACKS below (ai, ml, engineering by default;
        rename them to fit your field)

Creates roles/<role_id>.tex from the track, plus a roles/<role_id>.yaml stub with
every field the gates in apply.py check. It deliberately does NOT create a cover
letter: that is written per posting, and copying one is how a stale company name
ends up in a letter.

Fill in the yaml, tailor the .tex (reorder and re-emphasise; never add a claim
that is not in profile/master-profile.yaml), then run apply.py.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACKS = ("ai", "ml", "engineering")

# Same rule as tools/apply.py: role ids become folder names under out/.
ROLE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")

STUB = '''company: {company}
role: {role}
track: {track}
location: TODO
url: TODO                 # the posting where you found it
apply_url: TODO           # the employer's own application page, not an aggregator
portal: TODO              # workday | successfactors | personio | greenhouse | lever |
                          # linkedin_easy_apply | indeed_apply | other
source: TODO              # linkedin | indeed | watchlist | alert | you
fit_score: TODO           # 0-10, the rubric in .claude/skills/hunt/SKILL.md
language_gate: TODO — quote the posting's own words, and check the Profil/Qualifikation
  section rather than the language the advert is written in
filled: false             # when the form was filled up to Submit and left open in Chrome
left_for_you: []          # what you still do in that tab before pressing Submit
submitted: false
jd: jds/{rid}.md          # SAVE THE POSTING. Keyword scoring against a remembered
                          # requirement list is unverifiable; apply.py fails on it.
required_documents: [enrollment]   # add transcript when the posting asks for one
blockers: []
flags: []
must_have: []             # terms lifted from the posting's requirements section
nice_to_have: []
known_gaps:               # these belong HERE and in interview prep — never in the
  - TODO                  # cover letter. See SWEEP.md, "Never volunteer a gap".
'''


def main():
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    rid, track, company, role = sys.argv[1:5]

    if not ROLE_ID.match(rid):
        sys.exit(f"role_id may only use letters, digits, '.', '_' and '-': {rid!r}")
    if track not in TRACKS:
        sys.exit(f"track must be one of {', '.join(TRACKS)} — got '{track}'")

    src = f"{ROOT}/tracks/{track}.tex"
    if not os.path.exists(src):
        sys.exit(f"{src} missing — ask Claude to build tracks/{track}.tex from profile/master-profile.yaml")

    tex = f"{ROOT}/roles/{rid}.tex"
    yml = f"{ROOT}/roles/{rid}.yaml"
    for p in (tex, yml):
        if os.path.exists(p):
            sys.exit(f"{os.path.relpath(p, ROOT)} already exists — pick another role_id")

    # The track's first-line "% BASE TRACK" note belongs to the track, not to this
    # copy; replace it with where the copy came from.
    body = open(src).read()
    first, _, rest = body.partition("\n")
    if first.startswith("% BASE TRACK"):
        body = rest
    open(tex, "w").write(f"% Tailored for: {rid}  (started from tracks/{track}.tex)\n" + body)

    # JSON strings are valid YAML, so names with colons or quotes cannot break the file
    open(yml, "w").write(STUB.format(company=json.dumps(company, ensure_ascii=False),
                                     role=json.dumps(role, ensure_ascii=False),
                                     track=track, rid=rid))

    print(f"  roles/{rid}.tex   <- tracks/{track}.tex")
    print(f"  roles/{rid}.yaml  <- stub")
    print(f"\n  Next: save the posting to jds/{rid}.md, fill the yaml, tailor the tex,")
    print(f"        write roles/{rid}.cover.tex, then:")
    print(f"        .venv/bin/python tools/apply.py {rid}")


if __name__ == "__main__":
    main()
