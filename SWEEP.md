# Job sweep — sources and survival rules

The procedure lives in `.claude/skills/hunt/SKILL.md` (type `/hunt`), and your settings and
watchlist in `run.yaml`. This file is the reasoning behind them and the rules that decide
whether an application survives.

## What a run does and does not do

Collect, filter, verify, build documents, fill the form, stop before Submit, reach people
on LinkedIn. You review and submit every application yourself.

**Never submit unattended.** Portals need your logged-in session, and the human check keeps
catching things a bot would have sent: a company that already rejected you, a withdrawn
role, a language requirement above your level, a form question with legal consequences.

## Cadence

Once or twice daily. Do not stretch beyond daily: one role had 44 applicants an hour after
posting.

## Sources, and what each is worth

From the original search (Aug–Sep 2026):

- **LinkedIn** was the best source by a distance. `/hunt` searches it in your Chrome with
  the queries in `run.yaml`, newest first; the two queries' result sets barely overlap, so
  run both. The "More jobs" sidebar on a good posting is worth a look.
- **Employers' own career boards** are best of all, because a posting there is live by
  definition. List them in your watchlist, `search.watchlist` in `run.yaml`.
- **Indeed**: through the Indeed connector when it is connected, otherwise in Chrome.
- **StepStone** was weak for student roles; **Xing** had volume and near-zero viability.
  Both are covered, if at all, by email alerts in Gmail.

Aggregators show postings that already closed: six roles that looked live had been taken
down on the employer's site. `/hunt` verifies every lead on the employer's own board
before building anything.

## The filter that kills the most roles

A language requirement above your level. Read the Qualifikation/Profil section, not the
language the advert is written in. Applicant counts above roughly 80 on an aggregator are
the second: `/hunt` scores them down rather than dropping them, and reports the number.

## The rules that decide whether an application survives

- **One page, always.**
- **Never volunteer a gap.** No paragraph naming what you lack, in a letter or in outreach.
  Replace it with why this employer and what you would want to get right first.
- **Never drop an employment entry** to fit one page. Trim bullets, skills, coursework.
- **No hedges in a skills list** ("familiar", "basics"). Drop the weak item instead.
- **Every course named on the CV must be on the transcript.**
- **Render every PDF to an image and look at it.** Text extraction has called broken PDFs fine.
- **Check summary numbers against dates on the same page** ("three years" above two years of dates).
- **Writing reads as human.** No dash-asides; `apply.py` warns on em dashes.

## Answers for application forms

All in `profile/master-profile.yaml`: contact, split phone format, address, available-from,
hours, salary expectation, work permit, language levels. Voluntary questions (gender,
disability), consent boxes and anything the profile does not answer are left to you and
listed in the role's `left_for_you`.

## Recording outcomes

Every role YAML carries `filled:` when its form was left open for you, `submitted:` once you
press Submit, then `rejected:`, `dropped:` or `accepted:` once an answer arrives. Add it the
day the email lands; `/hunt` also catches confirmations and rejections in Gmail at the start
of each run. A role in `roles/` is never suggested again.

## Optional: a cloud digest between runs

`/hunt` needs your computer and Chrome. For a lighter check while you are away, type
`/schedule` in Claude Code and ask for something like:

> Every day at 08:00 Europe/Berlin, read the job-alert emails in my Gmail from the last
> 24 hours and check these career pages: <paste your watchlist URLs>. Drop roles that
> require German above <your level>, skip companies I already applied to (search my
> Gmail), and email me a short digest with the employer's own apply link for each role.
> Do not apply to anything.

It runs in the cloud with **no access to this folder**, which is why the watchlist and your
language level go into the prompt itself. Treat its digest as leads for your next `/hunt`.

## Watchlist

Your watchlist lives in `run.yaml` (`search.watchlist`), not here: which employers you
watch is yours, and `run.yaml` never gets pushed. This file is shared with everyone who
gets the kit, so keep it free of personal details.
