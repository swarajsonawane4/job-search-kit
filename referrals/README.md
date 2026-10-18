# Referral outreach — the staged approach

The point is that **nobody is asked for a referral cold**.
A referral is the outcome of a conversation that was worth having anyway, and asking
before that conversation exists converts badly and burns the contact permanently.
So `/hunt` reaches people on day one, and the referral ask comes days later, only if the
conversation earned it.

## The five stages

Each contact sits at exactly one stage. A contact only advances when they have actually
responded: accepted the request, or replied. `tools/referral.py` refuses to draft a later
stage otherwise, and refuses to draft the same stage twice while you wait.

**1. `connect`** — a connection request. Names the shared hook (same-university
alumni, or the specific role) and nothing else. **No ask of any kind.** The note cap
depends on the account (`linkedin.account` in `run.yaml`): 200 characters on a free
account, which also gets only a few personalised notes a month, and 300 on Premium. The
tool enforces the cap. When the notes run out, the request goes without one.

**2. `opener`** — once they accept. Two sentences on what you actually build,
then one genuine question about the role or the team. Short.

**3. `culture`** — the real questions, and they must be real: what the day-to-day
tasks look like, how the team works, what a good first six months looks like there.
This stage exists because the answers are useful whether or not a referral follows.
Do not fake curiosity here; the reply shapes stage 4.

**4. `fit`** — respond to what they actually said. Map your shipped work onto the tasks
they described, in their words. This one is never a template: the tool fails it until the
contact's `custom_fit` field holds the real message.

**5. `ask`** — only now, only if stage 4 drew a positive response, and only once the
application is submitted. Polite, specific, and easy to decline: name the requisition, say
the application is in, and ask whether they would be comfortable flagging it internally.

Then `thanks`, whatever the answer. A contact who says no this time is still a contact.

## The gates that matter

`tools/referral.py` will not draft stage 5 unless the contact's record shows
`last_reply_sentiment: positive` and the role's YAML shows `submitted:`. That is the
mechanical version of the rule: *ask for a referral only if the conversation turned out
positive, and only for an application that exists.* If the signal is neutral or absent,
the honest move is to stay at stage 4, or stop.

A reply counts as positive only when the person offers help or invites more contact.
Anything unclear is neutral.

Until the application is submitted, the messages say "I'm applying for", not "I just
applied": `/hunt` reaches people while the form still waits for your Submit.

## Who to reach for a role

In this order, two people per role by default (`run.contacts_per_role`):

1. **People named on the posting**: "Meet the hiring team" on the LinkedIn job, or a
   contact person in the posting text. Route `hiring_team`.
2. **Team members**: the company's People tab, searched for the team or function in the
   posting, e.g. `/company/<slug>/people/?keywords=machine+learning`. Route `peer`.
3. **Alumni**: the same People tab, searched for your university. Route `alumni`.
4. **A recruiter** for the company, only when the first three gave fewer than two.
   Route `recruiter`.

Prefer one `hiring_team` and one `alumni` or `peer`. At most two people per company in one
run, across all its roles, and never someone already in `contacts.yaml`.

## Rules inherited from the applications

The cover-letter lessons apply verbatim to outreach, because the failure mode is
identical.

- **Never volunteer a negative.** No "I know I'm probably underqualified", no
  apologising for reaching out, no listing what you lack. The linter in
  `tools/apply.py` is reused here.
- **No dash-asides.** Commas, colons, or separate sentences.
- **Never claim a connection that does not exist.** Alumni status is real and checkable;
  a shared interest invented to open a door is not.

## What goes in `contacts.yaml`

Name, title, employer, LinkedIn URL, the role it relates to, how the connection is
justified, current stage, and a dated log of what was sent and what came back.
Nothing else. This is a conversation tracker, not a dossier: do not collect personal
details beyond what LinkedIn shows publicly for professional contact.

## Channel and sending

**LinkedIn, not guessed email addresses.** Guessing firstname.lastname@employer.de either
bounces or lands as an unsolicited message to a corporate inbox. Use email only where the
employer published an address for the purpose.

**Who presses Send** is `linkedin.outreach` in `run.yaml`:

- `send`: Claude sends each request and message from your Chrome, after the tool passes
  it, within the run's LinkedIn limits.
- `type`: Claude types each message into the LinkedIn box and leaves it unsent; you read
  it and press Send.
- `off`: no outreach.

LinkedIn's User Agreement bans bots and automated messaging, and the account at risk is
yours. With `send`, the limits in `run.yaml` keep each run small, and at the first CAPTCHA,
warning or limit notice every LinkedIn action stops for that run.

**The commands:**

```
tools/referral.py due                  what to send next, what is blocked, who you wait for
tools/referral.py draft <id>           the message for the current stage, with its checks
tools/referral.py sent <id>            record it as sent (add --no-note for a bare request)
tools/referral.py accepted <id>        they accepted the request: stage 2 is due
tools/referral.py reply <id> <positive|neutral|negative> "their words"
```

`/hunt` runs these itself: it checks LinkedIn for accepts and replies first, then sends
what is due, then reaches new people.
