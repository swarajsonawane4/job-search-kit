# SAP SuccessFactors

Common at large companies and research institutes.
Hosts vary by employer (for example `career5.successfactors.eu`). Each host is a
separate domain for the Chrome extension and needs enabling individually.

## Order of operations — this one matters more than anything else

**Upload documents FIRST, fill fields SECOND.** Uploading a resume triggers a
server-side parse that rewrites the candidate profile and re-renders the whole
form. Everything typed beforehand is discarded, added rows disappear, and every
element id is regenerated. On 21 Aug 2026 this wiped a complete pass over one
form and it all had to be redone.

## Attachments

- There **is** a real `input[type=file]`, contrary to the earlier note here. It does
  not exist until the upload menu is opened: click the slot's pencil or plus, a
  menu offers "Upload from Device / Dropbox / Google", and at that moment an
  `input[type=file]` appears in the DOM. Locate it with `find` and drive it with
  `file_upload`. Never click "Upload from Device" itself — that opens the native
  picker, which cannot be driven.
- **PDFs with hyperlinks are rejected**: "The system does not allow files with
  active contents." Our LaTeX builds embed link annotations for GitHub, LinkedIn
  and email, and SAP's scanner refuses them. `tools/apply.py` already writes
  link-free copies: upload from `out/_upload/<role_id>/no-links/`. The URLs remain
  as visible text, so nothing is lost but the click.
- Where a posting asks for several certificates "ideally as one file", merge the
  `no-links/` copies into a single PDF.

## Skills

The resume parse silently adds skills — on one application it added 51, taking
the list from 98 to 149. **The cap is 100 and exceeding it blocks submission.** The chips are
buttons inside `div[class*="candidateSkills"]`, reachable through shadow DOM;
clicking one removes it. Expect to prune, and watch for mis-parses: "Transformers"
had been stored as "Electrical Transformers", which reads as the wrong discipline
entirely.

## Widgets

- **Dropdowns** are `<id>:_selectButton` plus `<id>:_input`, with options as
  `li[role="option"]`. Two lists can be open at once, and a click then lands on
  the wrong one — this silently set "legally authorized to work" to No and
  "previously employed by this company" to Yes. Close any open list, pick one control at a
  time, and verify each result before moving on. Batching several picks into one
  call also freezes the renderer.
- Long lists filter by typing into the input, but only on a prefix of the stored
  name. If your university is absent from the school list, the
  right answer is `*** School Not On List ***`, never the High School variant.
- **Dates** are UI5 web components in shadow DOM
  (`UI5-DATE-PICKER-XWEB-CALENDAR-WIDGET`). Set `.value` on the host, fire
  `change`, and also set the inner shadow input. Saved rows arrive oldest-first
  while the form asks for most-recent-first, so the dates need reordering to match
  the employers.
- Plain text fields need the native value setter plus input/change/blur events.

## Known-good answers

Phone goes in as one field with country code and no spaces, e.g. `+4915512345678`.
Set the German level to what your certificate says and check it every time; the stored
profile can drift upward (see below). Pick the closest "Area of study" and use the same
choice on every application.

## Left to you

Account creation and sign-in, the Sanction Party Screening consent, the gender
self-identification question, and Apply.

## Applying to a second requisition — 21 Aug 2026

The saved profile auto-attaches the previous application's documents. The second
application opened with the first role's resume and cover letter
already in the Resume and Cover letter slots, both
tailored to the earlier role and one of them naming the wrong role in its first line.
**Check the two document slots before anything else on every repeat application.**

Replacing them works: pencil on the Resume slot opens the source menu and the
`input[type=file]` appears; the Cover letter slot has no pencil, only a trash icon,
so delete first (an in-page Confirm dialog, not a native one) and the slot turns into
"Attach a Cover Letter" with a plus. The layout shifts by ~35px each time the green
success banner appears and clears, so re-screenshot before every click rather than
reusing coordinates.

**The skills cap fires on repeat applications too.** The parse of the new resume took
the list to 141 against a cap of 100. Removing chips through the shadow DOM works
(141 → 96), but a later Save re-synced the list to 99 with a different subset: several
pruned items came back. Under the cap is what matters; do not spend a second pass
trying to hold an exact set.

**Clicks near the Job-Specific section land unpredictably.** Expanding that section
while a dropdown is open set the gender question to Male and ticked the Sanction Party
Screening consent without either being clicked directly, which is the same two-lists-open
hazard already recorded above, now seen with a section header rather than a second list.
Both fields belong to you. Verify them with JavaScript rather than from a screenshot,
because the rendered state lagged the real value more than once. `find` also reported the
consent checkbox as `ref_948`; clicking that ref did not toggle it.

## The attach controls need real mouse events — 22 Aug 2026

On one employer's instance the pencil and plus icons do not respond to `element.click()`, and the
label reading "Attach a Cover Letter" is not the control at all. The control is the icon
underneath it, `span.glyphicon-plus-sign` inside `div.attachActions`, which sits inside
`div.attachmentBtn` (`<id>:_attach`). Clicking the label does nothing and returns no error,
which is what makes this expensive to diagnose.

What works is dispatching the full sequence on the element under the icon's own centre:

```js
function fire(el){
  const r = el.getBoundingClientRect();
  const cx = Math.round(r.left + r.width/2), cy = Math.round(r.top + r.height/2);
  const o = {bubbles:true, cancelable:true, clientX:cx, clientY:cy, view:window, button:0};
  const t = document.elementFromPoint(cx, cy) || el;
  ['pointerdown','mousedown','pointerup','mouseup','click']
    .forEach(n => t.dispatchEvent(new (n.startsWith('pointer') ? PointerEvent : MouseEvent)(n, o)));
}
const act = deepAll(document, 'div.attachActions')
  .find(a => /Attach a Cover Letter/i.test(a.textContent || ''));
act.scrollIntoView({block:'center'});
fire(act.querySelector('span.glyphicon, span, a, button') || act);
```

`pointerdown` and `mousedown` are the ones that matter; `click` alone is ignored. Afterwards
the `input[type=file]` exists and `find` locates it for `file_upload` as before. Select the
attach row by the text of its own `div.attachActions` rather than by a `ref`, because refs go
stale every time the upload re-renders the section.

**A dropdown will not close with Escape.** Neither a keyboard event on the select button nor
one on the body dismisses an open `li[role="option"]` list, and leaving it open is what makes
a later click land on the wrong control. The way out without answering the question is to
click the list's own **"No Selection"** option: the list closes and the field reads
"No Selection", which is the unanswered state. Use this for any question that belongs to
you, such as the compulsory-versus-voluntary internship question.

**Screenshot coordinates are scaled.** The screenshots came back 1568 wide against a
1920 viewport, a factor of about 1.22, so a coordinate read off the picture lands roughly
350px left of where it looks. Compute `window.innerWidth/1568` and multiply, or better,
use `getBoundingClientRect()` on the element and never read a coordinate off an image.
Asserting the target with `elementFromPoint` before clicking caught this immediately.

## Language level drifts upward — 22 Aug 2026

The saved candidate profile on one employer's instance stored German as **Intermediate**
although the real level was A2, and it arrived that way on a fresh application. That
contradicts `never_claim`. Reset it on every application until the stored profile itself
is corrected, and verify after setting.

The same stored profile also dropped one of three jobs from Work Experience and typed the
bachelor's degree as "School (secondary education)". Check the parsed Work Experience and
Education rows against your CV on every repeat application.
