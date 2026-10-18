# Driving a portal without burning the context window

The method for every site `/hunt` works on: employer portals, LinkedIn and Indeed.

Written 21 Aug 2026, after one SuccessFactors application cost roughly twenty-five
screenshots and, more importantly, produced two wrong actions because of them.

## The problem, stated honestly

A screenshot of a 1568x764 viewport costs on the order of a thousand tokens. A JavaScript
call that returns `consent=true gender=Male` costs about thirty. On that form the
screenshots were not only the largest single expense of the session, they were the cause
of two defects: the page shifts by about 35px whenever a green success banner appears and
clears, so coordinates captured in one screenshot were stale by the time they were clicked.
That is how the Sanction Party Screening consent got ticked and the gender question got set
to Male without either being clicked deliberately.

**Screenshots are not just expensive, they are the least reliable way to drive a form.**
Pixels tell you what the page looked like a moment ago. The DOM tells you what is true now.

## The order to reach for things

1. **Verify with JavaScript, never with your eyes.** After any action, return the specific
   values you care about as one short string:

   ```js
   const v = id => document.getElementById(id).value;
   `authorized=${v('517:_input')} residence=${v('555:_input')}`
   ```

   One line, thirty tokens, and it is the actual state rather than a rendering of it.

2. **Click by ref, not by coordinate.** `find` returns element references that survive
   layout shifts; coordinates do not. `computer` accepts `ref` in place of `coordinate`.
   Use coordinates only when no ref exists.

3. **One orientation screenshot per unfamiliar page.** Take it, learn the layout, then work
   through the DOM. Take a second only when something behaves unexpectedly and the DOM does
   not explain why.

4. **Never screenshot to read text.** `get_page_text` for prose, a targeted JS slice for a
   section. On LinkedIn, job descriptions may not appear in `read_page`; use
   `get_page_text` or a JS slice of the description element. Never call LinkedIn's
   internal APIs.

5. **Batch with `browser_batch`.** Action plus verification in one round trip. Note that
   coordinates inside a batch refer to the screenshot taken *before* the batch ran, so
   never batch a sequence of coordinate clicks that depend on each other.

6. **Before clicking anything irreversible, assert the target.** Read the element's own text
   and confirm it is what you think it is:

   ```js
   const el = document.elementFromPoint(x, y);
   el.tagName + ' | ' + el.textContent.trim().slice(0, 40)
   ```

   On that form, Apply sat a few hundred pixels from the controls being edited. A stray
   click there submits an application. This check costs nothing and is the difference
   between a mistake and a disaster.

## A filled form stays where it is

`/hunt` fills each application in its own tab and leaves it open for the owner to submit.
So, on a tab that holds a filled form:

- **Never navigate away, reload or close it.** Leaving a filled form raises the
  browser's "Leave site?" dialog, and a dialog freezes the extension until a human
  dismisses it. Open anything else in a new tab.
- **Save, never send.** If the portal has Save or Save as draft, use it. The final
  button (Submit, Apply, Send, Absenden, Senden, Bewerbung abschicken, Finish) is the
  owner's. Assert the target with the check in point 6 before every click on that page.
- **Write down what is left.** Every field left for the owner goes into the role YAML's
  `left_for_you`, so the hand-over lists it next to the tab.

## Where a screenshot is still the right tool

- First look at a page whose structure is unknown.
- Diagnosing a failure the DOM does not explain.
- Confirming a canvas or image-only widget.
- Looking at a rendered PDF before it goes out. That rule stands and is unrelated to cost:
  text extraction has twice reported a document as fine when it was visibly broken.

## The screen filter: see the page as controls, not pixels

Two filters exist over the live page and they answer different questions.

- `read_page` with `filter: "interactive"` answers *what can I act on?* It returns every
  button, link, combobox and input with its label and a `ref`. On a SuccessFactors page
  that is roughly 200 tokens against 1000+ for a screenshot of the same view. The `ref` is
  a stable handle: `computer` accepts `ref` in place of `coordinate`, so nothing depends on
  where an element happened to sit when the picture was taken.
- `find` answers *where is the thing I am looking for?* Natural language in, refs out. This
  is how the hidden `input[type=file]` was located on each upload slot.

Neither reports current field *values*, which is exactly what matters when filling a form.
So pair them with this scan, which returns label, value and a usable id for every field on
the page in one call:

```js
function deepAll(root, sel, out = []) {
  root.querySelectorAll(sel).forEach(e => out.push(e));
  root.querySelectorAll('*').forEach(e => { if (e.shadowRoot) deepAll(e.shadowRoot, sel, out) });
  return out;
}
const clean = s => String(s || '').replace(/[=%&?;]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 45);
deepAll(document, 'input,select,textarea')
  .filter(e => !['hidden', 'file', 'password'].includes(e.type))
  .map((e, i) => `${i} ${clean(e.getAttribute('aria-label') || e.name)} :: ` +
                 `${e.type === 'checkbox' ? e.checked : clean(e.value)} :: #${e.id}`)
  .join('\n');
```

The `deepAll` walk matters: SuccessFactors puts UI5 date pickers and skill chips inside
shadow roots, where a plain `querySelectorAll` finds nothing. The `clean` filter strips
`= % & ? ;` because the browser tool refuses output that looks like cookie or query-string
data, and SAP element ids are full of it.

Password boxes are skipped on purpose. Never read, type or store a password or a
one-time code, by scan, by JavaScript or by screenshot: sign-in pages are the owner's.

That is the whole loop, with no pixels in it: scan to see the form and its values, `find`
or `read_page` for a ref, act by ref or by setting the value directly, then re-run the scan
on just the fields you touched to confirm. Screenshots become a diagnostic tool for when
this loop reports something that makes no sense, rather than the way the work gets done.

## Known cheap, unknown once — the loop that keeps it that way

The steady state is that a form you have seen before costs no pictures at all: scan it,
act by ref, confirm by scan. That only stays true if every surprise is paid for once.

So when the page does something the recipe does not cover:

1. **Spend the screenshot.** One picture, deliberately, to see what actually happened. This
   is what screenshots are for and there is no point being stingy here.
2. **Work out the mechanism**, not just the fix. "Clicking the plus made a file input appear
   in the DOM" is reusable. "I clicked around and it worked" is not.
3. **Write the finding into the recipe** for that ATS — `portals/successfactors.md`,
   `workday.md`, `personio.md` — or into this file if it is about method rather than one
   system. Record the selector, the sequence, and the trap. Do not save the image; it will
   mean nothing in a month and the finding is what carries.
4. **Next encounter is text-only**, because the unknown became known.

Every entry in these recipes was bought this way. The hidden file input, the annotation
rejection, the 100-skill cap, the dropdown that fires on a neighbouring control: each cost
one confused session and now costs nothing. A recipe that stops growing is a recipe that
has stopped being read.
