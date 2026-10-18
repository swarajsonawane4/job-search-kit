# Workday

Common at large companies.

- **One account per employer.** Each company's Workday is its own site
  (`<company>.wd<n>.myworkdayjobs.com`) with its own account, so a sign-in at one
  does nothing for the next. Record each in `portals/accounts.csv`: company, login
  URL, username. Never the password.
- **Sign-in and account creation are yours.** `/hunt` leaves a Workday tab on its
  sign-in page, fills every other application, and lists the sign-ins together at the
  end. Sign in to all of them, say `continue`, and it fills those too. "My
  Information" is best checked by you; the rest fills cleanly.
- **Real multi-file input.** All demanded documents go up in one `file_upload`
  call — CV, cover letter, transcript together. This is the fastest of the three
  ATS families for attachments.
- Record degrees in the portal's own wording (e.g. "M.S. Master of Science").
- **Field of Study: leave blank.** It is an optional nested category picker that
  costs several round trips, and the transcript states the field anyway.
- Languages: pick the honest reading of your certificate (A2 = Beginner).
- Application Questions at the end (age declaration, expected gross salary,
  future-contact consent) are yours to answer, not Claude's.
