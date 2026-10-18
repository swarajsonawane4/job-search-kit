# Portal recipes

One file per applicant-tracking system, written the first time we meet it and
corrected every time after. The point is that the second application on a portal
should be mechanical: no rediscovering that a phone field must be split, or that a
file input is a decoy.

Method that makes these fast, established 21 Aug 2026 after the owner said the
click-through pace was too slow:

1. `read_page filter:"interactive"` once, to get refs for every field at once.
2. `form_input` per ref, batched through `browser_batch` — not click, type, screenshot.
3. `file_upload` against the real `<input type=file>` ref. Never click an upload
   button: it opens a native picker that cannot be seen or driven.
4. Screenshot only at the end, to verify the finished form before handing it over.
5. Where a portal offers "prefill from CV", use it. A resume that passes the parser
   checks in `tools/apply.py` (single column, standard headings, readable dates,
   text in reading order) usually prefills well, leaving a few fields to correct.
   Always check what the parse stored; see `successfactors.md`.
6. Upload from `out/_upload/<role_id>/`, which `apply.py` fills only after every gate
   passes. SuccessFactors refuses PDFs with clickable links: use the `no-links/` copies.
7. One tab per application, left open at the final step. Never navigate away from a
   filled form (see "A filled form stays where it is" in `browser.md`).
8. A portal that wants a sign-in or a new account: leave the tab on that page, list it in
   the role's `left_for_you`, and carry on with the next application. The sign-ins are
   handed over together at the end; after the owner says `continue`, those forms are
   filled too. `accounts.csv` here lists which employer portals the owner has accounts
   on (company, portal, login URL, username). It never holds a password.

Always stops before Submit. Voluntary and sensitive questions, consent boxes, account
creation and any login behind your fingerprint stay with you. Salary is filled only with
the figure in `master-profile.yaml`, exactly as written.

`browser.md` is the method rather than a recipe for one ATS: how to drive any of these
forms through the DOM instead of through screenshots, why coordinates go stale mid-form,
and the assertion to run before clicking anything irreversible.
