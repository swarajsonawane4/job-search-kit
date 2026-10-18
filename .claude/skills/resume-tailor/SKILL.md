---
name: resume-tailor
description: Tailors a resume to a job description using master-profile.yaml, never inventing facts. Use whenever a job posting is shared or a resume/CV needs adapting for an application.
---

# Resume tailor

Turn a job description plus `master-profile.yaml` into a one-page, honest,
role-specific resume — and say plainly when the role isn't worth applying to.

## Inputs

- `master-profile.yaml` — the only source of factual content. Find it in the
  working directory or ask the user for the path.
- A job description — pasted text, a URL, or a saved file.

If the profile file is missing, stop and ask. Do not reconstruct it from an
existing PDF resume; that resume is a lossy, already-tailored artifact and
building from it compounds earlier edits.

## The rule that matters most

Every claim in the output must trace to a specific entry in
`master-profile.yaml`. You may reorder, select, compress, and rephrase. You may
not add.

This sounds obvious and is the single easiest thing to get wrong, because
tailoring pressure is fabrication pressure. The JD asks for Kubernetes; the
profile mentions Docker; the tempting move is "containerized deployment
experience." That is a lie with good manners. If it isn't in the file, it does
not go on the page — and you say so in your notes back to the user instead.

Before writing, read `never_claim`. Check every drafted bullet against it.

## The other rule: never volunteer a gap

Honesty about what the profile does not contain belongs in your notes back to
the user, and in an interview when someone asks. It does not belong in the
documents.

Three applications sent in August 2026 were rejected within one, two and three
days. All three cover letters carried a paragraph opening "Where I fall short"
or "What I cannot claim" that listed disqualifying gaps in the applicant's own
words. One employer then rejected with almost the sentence that paragraph had
invited. Another letter explicitly negated two of the seven bullets in the
posting's own profile section.

A first-pass screener is filtering, not evaluating. A paragraph of gaps is a
pre-written rejection rationale handed to them on the page that decides whether
an interview happens. So:

- Do not write a gap paragraph, however well phrased.
- Do not hedge inside a skills list either. "GCP / Vercel / Firebase
  (familiar)", "CI/CD concepts", "TypeScript (working level)", "LangGraph
  (LangChain same ecosystem, quick to adopt)" all read as padding and discount
  the whole line. Drop the weak item instead of qualifying it. Removing a claim
  never overstates; keeping it without its qualifier does.
- Put the honest gap list in `known_gaps:` in the role YAML and in your notes,
  so the user walks into the interview ready for the question.
- Where the gap paragraph used to sit, write why this employer and what the
  user would want to get right first. That is what a screener is looking for.

## Process

**1. Parse the job description.** Extract, separately:
   - hard requirements (degree, years, language level, authorization, location)
   - core technical asks (the 3–6 things the role is actually about)
   - nice-to-haves
   - the vocabulary the company uses for these things

**2. Check for blockers first.** Compare hard requirements against the profile.
   If something is genuinely disqualifying — a language level they don't have,
   a sponsorship policy they can't meet, a seniority gap of several years — say
   so immediately, before doing any work. A fast "don't bother, here's why"
   is more valuable than a beautiful resume for a role that will auto-reject.
   Be honest about degree of blockage: "requires 5+ years" is usually soft;
   "requires C1 German" and "no visa sponsorship" are usually hard.

**3. Score and select.** Match `tags` across experience, projects, education,
   and skills against the core technical asks. Pull the highest-signal
   matching entries. Prefer:
   - a `strong` bullet with a real metric over three `medium` ones
   - a project that demonstrates the core ask over a job that merely mentions it
   - recent over old, unless the old thing is a direct hit

**4. Decide what to cut.** One page. Something has to go. Cut in this order:
   filler bullets, non-matching coursework, skills listed as `familiar` that
   the JD never mentions, then bullets from older roles until only the single
   strongest bullet on each remains.

   **Never cut an employment entry.** Trim its bullets to one line, never
   remove the job. A CV that lists one five-month role reads as someone with
   five months of experience and a gap in front of it, which is worse than the
   two lines the other jobs would have cost. This happened in August 2026: a
   trim left a single 2023 role on the page while the cover letter sent with it
   described "a year as an R&D intern" that appeared nowhere on the CV.

   After cutting, check the cover letter against the CV. Any employer or role
   the letter describes must be visible on the CV the reader has in front of
   them. `tools/apply.py` gates on this.

**5. Rewrite for the JD's vocabulary — honestly.** If the profile says
   "trained a classifier to sort incoming tickets" and the JD says "applied ML
   for text classification," rephrase toward their words. The underlying fact
   is unchanged; only the framing moved. Use the `evidence` field to check that
   your rephrasing still describes what actually happened.

**6. Write the output.** Then re-read every bullet once, cold, asking: could
   the user defend this sentence in an interview? Cut anything they couldn't.

## Output format

Build the resume as `roles/<role_id>.tex` in this folder, and the cover
letter as `roles/<role_id>.cover.tex`. Then produce the final documents with:

    .venv/bin/python tools/apply.py <role_id>

That single command compiles and gates in one step, and it is the only supported
way to produce a sendable document. The ten gates it runs are what catch the
failures that actually cost applications: a self-negating sentence, an employer
or job title named in the cover letter but dropped from the CV by a one-page
trim, a second page, a course the transcript does not list, hidden text, broken
ATS extraction, unreadable dates, a two-column layout. A file built any other way
has passed none of them and looks exactly as finished.

Do not produce a `.docx` by default. Export one only when a posting explicitly
demands that format. When you do, say so plainly in your report back, because
that file has bypassed every gate above and needs reading by eye before it is sent.

The compiled resume uses this order:

```
Name · Location · Email · Phone · GitHub/LinkedIn
Summary            (2 lines, rewritten per role — optional, cut it for space)
Experience         (reverse chronological)
Projects           (only those selected for this role)
Education          (thesis title only when relevant to the role)
Skills             (grouped, ordered by relevance to this JD)
Languages
```

Plain formatting: no columns, no tables, no text boxes, no icons, no headshot.
Those break ATS parsing, and `apply.py` fails a page where text sits side by side.
Standard section headings: "Experience," not "Where I've Made an Impact." The
section order above is the default, not a rule; `apply.py` only checks that the PDF
reads out in the order the .tex declares.

Filenames. The build writes `out/<role_id>/<role_id>.pdf` and
`out/<role_id>/<role_id>.cover.pdf`. Those names are for the pipeline, not for a
recruiter. When every gate passes, `apply.py` stages the upload set itself in
`out/_upload/<role_id>/`, under the names a human will read, together with the
required documents from `docs/`:

    Firstname_Lastname_CV_<Company>_<Role>.pdf
    Firstname_Lastname_CoverLetter_<Company>_<Role>.pdf

plus identical copies without clickable links in `no-links/`, for SuccessFactors
and any other portal that rejects "active content". A build that fails a gate
clears the folder. Upload from `out/_upload/<role_id>/`, never from
`out/<role_id>/`.

## Always report back

After producing the file, tell the user in plain prose:

- **Fit read** — a one-line honest assessment, not encouragement.
- **Gaps** — requirements the profile genuinely doesn't cover. Name them.
  This is what they prepare answers for, and it's the most useful thing here.
- **What got cut and why** — so they can overrule you.
- **Anything the JD wanted that you suspect they have but isn't in the
  profile** — this is how `master-profile.yaml` gets better over time. Ask
  them directly, then offer to add it to the file.

Never end with a confidence-boosting flourish. A flat, accurate read is more
useful to someone deciding where to spend their limited applications.

## Examples

**Rephrasing that is fine:**
Profile: `Built a pipeline to clean and label 40k scraped product listings.`
JD language: "data curation for training sets"
Output: `Curated and labeled a 40k-record product dataset for model training.`
— same facts, their vocabulary.

**Rephrasing that is not:**
Profile: `Used Docker to run experiments locally.`
JD language: "container orchestration at scale"
Bad output: `Deployed containerized ML workloads.`
Correct move: keep the honest bullet, and flag to the user that the role wants
orchestration experience they don't have.

**Blocker call:**
JD: "Verhandlungssicheres Deutsch erforderlich." Profile: German B1.
Correct response: stop, report the blocker, do not generate a resume.
