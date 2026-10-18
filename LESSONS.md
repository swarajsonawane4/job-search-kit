# Lessons

Every entry is a mistake that cost something in a real search (Aug–Sep 2026), and the rule
it produced. Add your own at the bottom: what happened, what changed, the general rule.

## A gap paragraph is a pre-written rejection

Three cover letters carried a paragraph opening "Where I fall short" that listed missing
skills. All three were rejected within one to three days, one with almost the same words.
**Rule:** never name a gap in a document. Keep gaps in the role YAML and prepare interview
answers. `apply.py` fails any letter containing self-negating phrases.

## A one-page trim deleted real jobs

To fit one page, a CV kept one five-month job and dropped eighteen months of earlier work.
It read as a gap, and the cover letter sent with it described a job the CV no longer showed.
**Rule:** never remove an employment entry; cut it to one bullet. `apply.py` checks every
employer in the profile is on the CV and every employer in the letter is on the CV.

## Invented coursework nearly reached an employer who reads transcripts

Two module names on the CV were plausible but not on the transcript.
**Rule:** every course named on the CV must match the transcript. `apply.py` checks it.

## A summary sentence overstated experience by a year

"Three years of engineering practice" sat on the same page as dates adding up to two. It
reached twelve files because the base CV generator carried it.
**Rule:** check any number in prose (years, projects, dataset size) against the structured
data on the same page, and fix the base track, not only the copy.

## Hedged skills discount the whole line

"TypeScript (working level)", "CI/CD concepts", "(familiar)" read as padding.
**Rule:** drop a weak item rather than qualify it.

## "Live" postings were dead

Six roles found on aggregators had already closed on the employer's own board.
**Rule:** click through and verify on the employer's site before building anything.

## A thank-you note reached one of three interviewers

A reply to the interview invite went only to the sender, while the greeting named three
people. **Rule:** before any reply to an employer, compare To/Cc with every name in the
greeting. Usually that means Reply All.

## Documents went to the wrong thread and opened a duplicate ticket

HR sent two emails; only one was read, and the documents went out as a new email instead
of a reply in the thread HR had asked for.
**Rule:** read every recent email from that employer before sending anything. When two
instructions differ, the one naming a specific thread or address wins.

## Portals re-parse your CV and overwrite what you typed

On SuccessFactors, uploading the CV re-rendered the form and wiped a full pass of typed
answers. It also stored a language level above the true one.
**Rule:** upload first, fill second, and re-check stored language levels every time.
See `portals/`.

## Screenshots are the least reliable way to drive a form

Stale screenshot coordinates caused two wrong clicks (a consent box and a gender field)
after a banner shifted the page.
**Rule:** read and set fields through the page structure, verify with a JavaScript read,
and assert the target before any irreversible click. See `portals/browser.md`.

## The tracker drifted

An offer was still listed as "awaiting reply" and five rejections were never logged.
**Rule:** start every session with `state.py` plus a Gmail check, and log outcomes the day
they arrive.
