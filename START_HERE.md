# Job search starter kit — start here

This folder turns Claude Code into your job-search assistant. One command, `/hunt`,
runs the whole search without stopping: it collects new roles from LinkedIn, Indeed,
employers' career pages and your job-alert emails, picks the best fits, tailors a
one-page CV and cover letter for each, fills every application in its own Chrome tab
and stops at Submit, then reaches at least two relevant people per role on LinkedIn on
the way to a referral. You read what it did, finish what it left for you, and press
Submit yourself. **It never submits an application and never sends an email.**

Everything personal is blank. You fill it in once, with Claude's help, and it stays on your
machine: see "Sharing the kit" at the end.

## LinkedIn: read this once

`/hunt` uses LinkedIn in your logged-in Chrome: it searches jobs, opens profiles, and
(with `linkedin.outreach: send` in `run.yaml`) sends connection requests and messages
as you. LinkedIn's User Agreement bans bots and automated messaging, and the account
that can be restricted is yours. The run keeps the volume small (limits in `run.yaml`)
and stops all LinkedIn actions at the first CAPTCHA, warning or limit notice. Prefer to
press Send yourself? Set `outreach: type`. Keep Claude off LinkedIn entirely: remove
`linkedin` from `search.sources` and set `outreach: off`.

## 1. Install (about 30 minutes)

1. **Claude plan.** Claude Pro, Max, Team or Enterprise (claude.ai). Sign in to Claude Code
   with `/login`; the Chrome integration does not work with an API key.
2. **Claude Code CLI.** Install Node.js from nodejs.org, then in a terminal:
   `npm install -g @anthropic-ai/claude-code`
3. **Unzip this folder** somewhere permanent, e.g. your home folder, and keep the name
   `job-search-starter-kit` (or rename it, e.g. `job-applications`).
4. **Run the setup script** from inside the folder:
   `cd ~/job-search-starter-kit && bash setup.sh`
   It creates a Python environment and tells you if LaTeX is missing (it prints the
   install command).

## 2. Connect your accounts (about 15 minutes)

| What | Where | Why |
| --- | --- | --- |
| Claude in Chrome | Chrome Web Store → "Claude", sign in with the same account | Fills applications and uses LinkedIn in *your* logged-in browser |
| LinkedIn, Indeed | Log in to both in that Chrome | `/hunt` searches them and reaches people there |
| Portal accounts | Log in to employer portals you already have accounts on | A portal that wants a sign-in is left for you, not skipped silently |
| Gmail (+ Calendar) | claude.ai → Settings → Connectors | Read confirmations, replies and job alerts; draft (never send) replies |
| Indeed connector (optional) | claude.ai → Settings → Connectors | Searches Indeed without opening it in Chrome |
| Job alerts (optional) | Save your searches as email alerts on StepStone and Xing | Extra leads that arrive in Gmail |

## 3. First session (about 1–2 hours, mostly talking)

In the folder, type `claude --chrome`, then say:

> Setup is new. Follow CLAUDE.md, first session.

Claude will interview you to fill `profile/master-profile.yaml` (every job, project, number,
course, language level, and a `never_claim` list), ask for your transcript and enrollment
certificate for `docs/`, build your base CVs in `tracks/`, set your searches and limits in
`run.yaml`, and start the employer watchlist there too.

Take the profile seriously. Every CV is built only from it. Anything you leave out can
never appear on a CV; anything wrong spreads to every application.

The first time, Claude Code asks you to trust the folder. Accept: that turns on
`.claude/settings.json`, which pre-approves the tools `/hunt` uses so it does not stop to
ask. Chrome may still ask once for each new site (a portal it has never acted on); allow
the site.

## 4. Running /hunt

1. Chrome is open and logged in to LinkedIn, Indeed and any portal accounts you have.
2. In the folder: `claude --chrome` (or run `/chrome` once and pick "Enabled by default").
3. Type `/hunt`, or `/hunt 3` for three roles this run.

It runs to the end without asking anything: catch up on replies, collect, filter and score,
build documents, fill the applications, outreach, hand over. A full run of five roles takes
a while; let it work. Everything it does is logged in `runs/<date-time>/log.md`.

When it finishes you get:

- **Tabs waiting for your Submit**, one per role, each with what is left for you
  (consent boxes, voluntary questions, a sign-in).
- **Outreach**: who was contacted for which role, and what was sent.
- **For you**: anything only you can do or decide.

Then: finish each tab, press Submit, and say `submitted <role_id> <role_id> ...`.
**Do not run /clear before submitting**: it closes the tabs with the forms in them. Exiting
Claude Code keeps them open. Portals can sign you out after a while, so submit soon.

## Portals that need a sign-in (Workday and others)

- **Each company's Workday is a separate account.** A sign-in at one employer does nothing
  for the next. List the accounts you have in `portals/accounts.csv`: company, portal,
  login URL, username. **Never a password**: a plain file in this folder ends up in every
  zip, sync and Claude transcript, and `state.py` warns if a password column appears.
- **Before `/hunt`, sign in to the portals you use.** Chrome keeps you signed in for a
  while, so those forms get filled straight through.
- **Anything still asking for a sign-in is queued, not waited on.** The run leaves that
  tab on its sign-in page and fills every other application first. At the end you get
  one list: sign in to each (let your password manager fill it in a click), clear any
  CAPTCHA, say `continue`, and it fills those too. That is the one sitting the run needs
  from you, next to pressing Submit.
- **CAPTCHAs stay with you.** They exist to check that a human is there; the kit hands
  them to you and never tries to get around them. They show up less when you are signed
  in and the run moves at a normal pace.
- **On a Mac with the Claude desktop app:** 1Password for Claude (beta) lets Claude sign
  in without ever seeing the password or one-time code; you approve each sign-in. Its
  documentation covers the desktop app with Claude in Chrome, not Claude Code in the
  terminal, so it may not work with `/hunt` as set up here.

## 5. Other things to say

| When | Say |
| --- | --- |
| You signed in to the queued portals | Continue. (Or: continue <role_id>.) |
| You submitted | Submitted <role_id> <role_id>. |
| Someone replied on LinkedIn | Check LinkedIn replies and send the follow-ups (or just run /hunt; it does this first). |
| One posting you found yourself | Tailor and fill this one, stop before Submit, and reach two people: <URL> |
| Status | Run state.py and tell me what's waiting on me. |
| Something went wrong | Add this to LESSONS.md with the rule it teaches: <what happened> |
| Got an offer | Mark it accepted, drop unsent roles, and stop running /hunt. |

## 6. The rules that matter most

- Claude prepares, **you** press Submit. It never sends an email, never touches a
  password, and never tries to get past a CAPTCHA.
- LinkedIn messages go out only as `run.yaml` allows, only after `tools/referral.py`
  passes them, and nobody is asked for a referral before a positive reply and a submitted
  application.
- Nothing goes on a CV that is not in your profile. Rephrasing is fine; inventing is not.
- Never write what you lack in a cover letter. Keep that for interview prep.
- One page. Never delete a whole job to make it fit.
- Verify a posting on the employer's own site before spending time on it.
- Upload only from `out/_upload/<role_id>/`. On SuccessFactors, use the `no-links/` copies.
- Read `LESSONS.md` once — every rule in there cost a real application.
- Before pushing the kit anywhere: `.venv/bin/python tools/check_share.py`.

## What's in the folder

Shared: travels with the kit when you push it.

| Path | What |
| --- | --- |
| `CLAUDE.md` | Instructions Claude reads automatically in this folder |
| `.claude/skills/hunt/` | The `/hunt` run, step by step |
| `.claude/skills/resume-tailor/` | The tailoring rules Claude follows for every posting |
| `.claude/settings.json` | Tools pre-approved so `/hunt` runs without stopping; sending email is blocked |
| `*.example.*` | The blank starting points for your personal files below |
| `template/` | CV and cover-letter LaTeX templates, ATS-safe |
| `tools/` | `newrole.py` scaffold · `apply.py` build, 10 gates and upload staging · `fit_one_page.py` · `state.py` tracker · `referral.py` outreach drafts and gates · `check_profile.py` says whether the profile is ready · `init_workspace.py` makes your personal files · `check_share.py` checks before a push |
| `SWEEP.md`, `portals/`, `referrals/README.md`, `LESSONS.md` | Sources and survival rules, portal quirks, the outreach method, lessons |
| `.gitignore` | Keeps everything in the next table out of git |

Personal: made by `setup.sh`, filled by you, never pushed.

| Path | What |
| --- | --- |
| `profile/master-profile.yaml` | Your facts, course names and enrollment date |
| `run.yaml` | Your searches, watchlist, roles and contacts per run, LinkedIn mode and limits |
| `portals/accounts.csv` | Employer portals you have accounts on: company, login URL, username. Never passwords |
| `referrals/contacts.yaml` | The people you reached on LinkedIn, and where each conversation stands |
| `tracks/` | Your base CVs (built in the first session) |
| `docs/` | Transcript, enrollment certificate, other attachments |
| `roles/`, `jds/` | One file set per application, saved postings |
| `out/` | Built PDFs; `out/_upload/<role_id>/` is what you upload |
| `runs/` | One log per `/hunt`: leads and scores, tabs, sign-in queue, outreach |

## Sharing the kit

Your details live only in the personal files above, and `.gitignore` keeps all of them out
of git. So you can push the folder and anyone who clones it gets the kit, blank, without
your profile, CVs, documents, accounts, contacts or search history. They run `setup.sh`
and get their own blank copies.

Before every push:

```
.venv/bin/python tools/check_share.py
```

It reads every file git would push and fails if a personal file is tracked, if a shared
file mentions your name, email, phone, street, LinkedIn or GitHub handle, a portal username
or a contact's name, or if any PDF is tracked.

Three things `.gitignore` cannot do:

- **Untrack a file that was committed before it existed.** Run `git rm --cached <file>`
  and commit; the file stays on your disk. `check_share.py` lists the exact commands.
- **Take back a push.** A file that was already pushed stays in the repository's history
  even after you delete it. Treat it as seen: for a public repository, remove it from
  the history (GitHub's guide: "Removing sensitive data from a repository") or start a
  fresh repository.
- **Watch the shared files.** `LESSONS.md`, the portal recipes and the docs travel with
  the kit. Write lessons without names, emails or the companies you applied to.

Sharing as a zip instead? Make it from git, so only the shared files go in:
`git archive -o ../job-search-starter-kit.zip HEAD`.
