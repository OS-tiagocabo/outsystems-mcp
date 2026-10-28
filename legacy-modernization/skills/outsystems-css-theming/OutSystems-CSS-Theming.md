# OutSystems CSS & Theming — where a rule actually applies, and why it "did nothing"

> Most "my CSS did nothing" / "my fix won't take" / "there are two arrows now"
> bugs in ODC are **not on the widget you're editing** — they're a wrong style
> input (`Style` vs `CustomStyle`), or a rule loaded from a *different* stylesheet
> than you think (block-stylesheet spillover). This guide is the load model + the
> consolidation fix + the corrected single-arrow recipe.
>
> For feature wiring see **outsystems-ui-recipes**; for the general build/mentor
> mechanics see **outsystems-app-build**; for editing a shared block's structure
> see **outsystems-block-editing**.

---

## 1. `Style` vs `CustomStyle` — the #1 "my CSS did nothing" bug

OutSystems widgets have TWO style inputs:

- **`Style` = CSS class name(s)** — a reference to a class defined in a stylesheet.
- **`CustomStyle` = inline CSS** — literal declarations (`background:#c00;color:#fff;…`).

Put inline CSS into **`Style`** and the browser treats the whole string as a bogus
**class name** → **silently ignored, no validation error.** This is a repeat
cause of wasted publish/retry cycles (an active-tab pill that never highlighted;
header link colours that wouldn't override — both because the rule sat on `Style`).

- **Rule:** inline CSS → **`CustomStyle`**; a class name (from the theme/screen
  stylesheet) → **`Style`**.
- When instructing Mentor, **name the property explicitly** ("set the tab's
  **`CustomStyle`** to `background:<brand-hex>;color:#fff;…`").
- **Tell:** a style change doesn't render and there's **no error** → suspect
  inline-CSS-on-`Style` first.

---

## 2. The ODC stylesheet load model — WHERE each rule really applies

Four places hold CSS, with very different real scopes. Know which one a rule lives
in before you touch it:

| Location | Real scope |
|---|---|
| **App Theme stylesheet** | Truly **GLOBAL** — loaded on every screen. The *only* place meant to be app-wide. |
| **Screen stylesheet** | Loaded ONLY while that screen is open. Safe for screen-local overrides *if* the selector is genuinely screen-specific. |
| **Block stylesheet** | Loaded whenever the block is **rendered**. A block used on one screen is screen-scoped in practice; **a block rendered on EVERY screen (a shared NavHeader / footer / menu) makes its stylesheet effectively GLOBAL.** |
| **Widget inline `Style` / `CustomStyle`** | Most specific, and the hardest to find later. |

**The spillover trap:** an unscoped **element** selector (`select{…}`, `input{…}`,
`.card{…}`) in a *shared block* stylesheet leaks into every screen and outranks
screen CSS by load order. No screen-scoped rule can win against it — because the
rule isn't on the screen at all.

---

## 3. The tell + the debugging move

- **Tell:** a CSS fix "won't take" no matter how tightly you scope it to the
  screen, OR a style you never authored on a screen appears there anyway, OR the
  symptom is identical on multiple unrelated screens → suspect a **shared block
  stylesheet** (especially a NavHeader/menu/footer that renders everywhere) with
  an **unscoped element selector**, or a rule already in the Theme.
- **Move:** inventory ALL four locations *before* patching — the Theme + every
  screen stylesheet + every block stylesheet + widget inline. Have Mentor dump
  each stylesheet's char-length and grep the offending selector across all of them.
  Do **not** keep patching the screen the symptom shows on.
- **Probe the live DOM with `browser_assert` + CSS selectors** when a style fix
  "doesn't take." You can't read computed styles, but visibility asserts on
  selectors (`.popup-dialog`, `.popup-content`, `.<yourclass> .popup-dialog`) tell
  you which classes EXIST and whether a scoped selector actually MATCHES — that's
  how you nail facts instead of guessing. Note: a heavy `box-shadow` can read as a
  faint "second card" halo in a screenshot — DOM-probe or hard-reload and look at
  edge sharpness rather than calling it off a screenshot alone.

---

## 4. The fix pattern — consolidate ALL custom CSS into ONE Theme

When styling has sprawled across screens/blocks/widgets (and especially once
spillover has bitten):

1. Create/keep a **single local Theme** (e.g. `<App>Theme`) extending
   `OutSystemsUI`; move ALL custom CSS there, in clearly **labelled sections**
   (one per screen/block) with **class names preserved**, merging duplicate
   selectors.
2. **Empty** every per-screen stylesheet, every block stylesheet, and clear widget
   inline `Style`/`CustomStyle`.
3. Result: nothing spills — there is exactly one stylesheet and it's *meant* to be
   global. Visual output is unchanged (same rules, same classes). **Verify** by
   screenshotting the main screens + one popup before/after; the only intended
   diff is the fixed symptom (e.g. the single arrow below).
4. **Replace, don't stack.** Before adding an override, search the Theme for EVERY
   existing rule on that class — Mentor's and your own from earlier turns — and
   rewrite or delete them in the same turn. Two `!important` declarations resolve
   by **specificity**, then source order, so a stale `.shell .page{position:relative
   !important}` silently beats a newer `.page{position:fixed !important}` and the
   new fix "does nothing". Rules written against an older DOM are landmines too: a
   hide rule aimed at a wrapper turned into "the whole dashboard is blank" once
   Mentor re-parented content inside that wrapper. Field-proven: two fix turns
   no-op'd until the live computed style was read and the leftover rules removed.
   **Do the search yourself and name the exact selectors to delete.** Never hand
   Mentor a pattern like "delete every rule whose selector contains `.<app>-pill` or
   `.<app>-table__btn`". It deleted those rules and also the tab-bar, KPI-card
   and rail rules in the same block, and a whole restore turn followed. When you
   cannot list the stale rules, append a block with a MORE specific selector and
   delete nothing.

---

## 5. Double-arrow / double-chevron on a dropdown — the CORRECTED recipe

Two arrows on a styled dropdown come from **two independent** sources, and the
common wrong fix (`appearance: auto`) is itself the spillover culprit:

- The ODC `Dropdown` widget renders `<div class="dropdown osui-dropdown"><select>…</select></div>`,
  and the OutSystemsUI base theme draws a chevron via **`.dropdown::after` on the
  WRAPPER div** — on top of the native `<select>` arrow. So a styled dropdown can
  show TWO arrows even after you strip every `background-image`/`appearance` off
  the `<select>` itself (the extra arrow lives on the *wrapper*, not the select —
  chasing it on the `<select>` loops forever).
- **Corrected recipe:**
  - Suppress the framework wrapper chevron **in the Theme**:
    `.dropdown::after, .osui-dropdown::after { display:none !important; content:none !important; }`.
  - Set **NO** `appearance` on `<select>` anywhere — neither `none` nor `auto`.
    Leave the browser default; it draws exactly one native arrow.
  - **Delete any stray `appearance: … !important` rule** — a global
    `select { appearance: auto !important }` (classically living in a *shared
    block* stylesheet like NavHeader, so it spills app-wide) forces the native
    arrow back and re-creates the double arrow. This is the exact regression the
    consolidation fix (§4) resolves.
- Net: one Theme rule kills the framework chevron; the untouched native `<select>`
  arrow is the only one left.

---

## 6. Popup "double card" / stray offset white rectangle behind a modal

- The ODC `Popup` widget renders a **3-level DOM: `.popup-dialog` → `.popup-content`**
  (there is **no** `.popup` element in ODC). The default OutSystemsUI theme puts
  card chrome (bg + radius + shadow + padding) on **`.popup-dialog`**.
- If you ALSO style `.popup-content` (or an inner modal-card widget) as a card, you
  get TWO stacked, slightly-offset cards — a ghost rectangle poking out behind.
  Don't keep a redundant transparent wrapper "just for layout" either — the popup
  IS the container.
- **Fix:** pick ONE element to be the card and strip chrome off the other(s). If
  you make `.popup-content` the card (delete any inner card widget via
  `Delete(preserveChildren:true)`; put layout `display:flex;flex-direction:column;
  gap:…` + chrome + `overflow:visible !important` on `.popup-content`), you MUST
  also strip `.popup-dialog`:
  `.popup-dialog { background:transparent!important; box-shadow:none!important; border:0!important; border-radius:0!important; padding:0!important; }`.
- **Scope gotcha:** the widget's `Style` class (e.g. `popup-no-chrome`) is NOT an
  ancestor of `.popup-dialog`, so a rule like `.popup-no-chrome .popup-dialog`
  matches NOTHING — target `.popup-dialog` **directly**. A Screen stylesheet only
  loads on that screen, so a direct `.popup-dialog` rule is safe there as long as
  that screen's only Popup instances are the ones you want stripped.
- (VirtualSelect / `DropdownSearch` renders its dropbox `position:fixed`, so it
  overlays fine once no ancestor has `overflow:hidden`.)

---

## 7. Model API note — reaching the Theme (hand Mentor the names)

To edit the local theme via the Model API, the eSpace exposes **`MobileThemes`**
(there is **no** `IESpace.Themes` member — Mentor otherwise burns a run failing
`CS1061: 'IESpace' does not contain a definition for 'Themes'`). A flow's theme is
**`flow.Theme`** on `eSpaceObj.MobileFlows.Named("MainFlow")`. Put these names in
the `mentor_start` prompt so Mentor edits the theme stylesheet directly instead of
exploring.

---

## 8. Link/nav colours that won't hold on every screen — the base OSUI `a{}` rule wins

Symptom: nav links (or any `Link`) keep rendering in the theme's default primary
colour with a hover underline, and a fix applied on one screen (or inline) does
**not** hold on every screen. Cause: the OutSystemsUI base theme ships an
**element** rule for `a{…}` (colour + `text-decoration` on hover). An inline
`CustomStyle` on one link, or a rule in a single screen's stylesheet, only wins
where it's placed — the base `a{}` rule wins everywhere else. This is the
link-colour case of the spillover model (§2/§3): the rule you're fighting lives in
the Theme, not on the screen the symptom shows on.

- **Fix at the Theme StyleSheet, ancestor-scoped, so it holds app-wide.** Put the
  nav-link rules in the app Theme keyed off the nav container so they beat the base
  `a{}` on **every** screen without touching each one:
  - inactive nav link → the design's muted colour
    (`.<nav> a { color: var(--nav-link); }`)
  - active nav link → the design's active colour + the accent underline
    (`.<nav> a.active { color: var(--nav-active); border-bottom: … var(--accent); }`)
  - hover → active colour, **no** text-decoration
    (`.<nav> a:hover { color: var(--nav-active); text-decoration: none; }`)
- **Kill the stray app-wide hover underline separately — but scope it so it doesn't
  strip the active underline.** An app-wide `a:hover { text-decoration: none; }` in
  the Theme removes the underline-on-hover everywhere; make sure the nav's *active*
  underline comes from `border-bottom` (not `text-decoration`) so this rule can't
  erase it.
- **Content links inherit the SAME base `a{}` — de-gold them app-wide too, not
  just the nav.** Scoping the fix to the nav container leaves every OTHER anchor
  (links inside detail / config / content areas) still rendering the theme's
  primary/accent colour — those are the "highlights" that reappear on content
  screens *after* the nav is fixed. Add a content-scoped Theme rule keyed off the
  shared content wrapper — e.g. `.main-content a { color: inherit;
  text-decoration: none; }` (`inherit` picks up the surrounding text colour) — so
  content links stop reading as clickable gold links everywhere at once.
  `main-content` is OSUI's own content-region class — which is exactly why the
  OSUI-idioms rule says never to *author* a class by that name (app-prefix your
  own: `<app>-content`). Targeting OSUI's wrapper in a Theme rule is the intended
  use of it, and is why a rule scoped there lands on every screen's body. Field-proven: gold "highlight" links kept
  reappearing on a system-config screen until a `.main-content a` Theme rule
  de-golded them — a nav-only fix was not enough.
- **Verify on more than one screen.** The whole point is that the base `a{}` won on
  screens you never patched — drive/reload at least two screens and confirm the
  inactive / active / hover states all hold.
- **Tell:** a link colour or underline is right on the screen you edited but wrong
  elsewhere → it's the base OSUI `a{}` rule. Move the fix to the Theme; don't keep
  patching per screen (§2/§3).

---

## 9. Reusable `mentor_start` skeleton — consolidate CSS into the Theme

> Inventory ALL custom CSS across the app Theme, every screen stylesheet, the
> `<SharedBlock>` (e.g. NavHeader) block stylesheet, and widget inline `Style`.
> Move it ALL into the app Theme's stylesheet (the local theme extending
> OutSystemsUI, reached via `MobileThemes` / `flow.Theme`) in labelled sections,
> class names preserved, duplicates merged. Then EMPTY every screen stylesheet, the
> block stylesheet, and clear widget inline styles. Remove any `appearance` rule on
> `select` (it spills app-wide from the block). Achieve exactly ONE arrow on
> dropdowns: `.dropdown::after {display:none!important;content:none!important}` in
> the Theme and NO `appearance` anywhere. Keep the app visually identical
> otherwise. 0 validation errors; screens stay Anonymous.

---

## 10. Adopting a SHARED theme (base-theme inheritance) — three traps

Pointing an app's theme at a shared/design-system theme as its **base theme** is
the cheap way to unify a suite's look (see **outsystems-osui-idioms**, "Consuming
a shared UI library"). It layers the shared theme's CSS **under** the app's — so
it's additive, and the additions can collide.

### 10a. Inherited pseudo-elements double up on shared class names

Inheritance injects every rule the shared theme defines, including
`::before`/`::after` content, onto **any class name the app happens to reuse**.
The field case: after the rebase every sidebar item rendered **two bullet dots** —
the app drew its own (`.<app>-nav-dot`) and the inherited
`.<app>-nav-item::before { content:"" … }` added a second, because the app's nav
links carry `.<app>-nav-item`. Sibling apps didn't collide (their nav links aren't
styled by that `::before`), so the collision is **app-specific and invisible
until you look**.

- **Audit right after the rebase:** diff the shared theme's selectors against the
  class names the app actually uses, focusing on **decorative pseudo-elements** —
  dots, arrows/chevrons, badges, counters, separators. Those are what double.
- **Fix at the app theme**, one targeted rule, not by renaming the app's classes:
  `.<app>-nav-item::before { content:none !important; display:none !important; }`
- Same failure family as the double-arrow dropdown (§5): a framework/base rule you
  didn't author drawing a second copy of something you did.

### 10b. `var(--token, #HEX)` — zero-risk token single-sourcing

To route an app's hardcoded palette onto shared design tokens **without any
visual risk**, replace each `#HEX` with `var(--token, #HEX)` — the original hex
stays as the fallback, so rendering is byte-identical whether or not the variable
resolves in that scope, while the app consumes the shared token wherever it does.
~113 hardcoded brand hexes were single-sourced this way in one turn, verified
identical by screenshot.

- Only swap values that **exactly match** a defined token. Leave generic
  whites/greys and genuinely app-specific colours hardcoded — a near-match swap
  is a silent visual change.
- The fallback is not optional: `var(--token)` with no fallback renders nothing
  when the variable is out of scope.

### 10c. "Duplicate CSS" — override vs parallel implementation

Read the actual stylesheet (`context_themes`, owned-only) **before** you scope a
CSS de-dup, and classify what you're looking at:

- **Override duplicates** — the app re-declares the *same selectors* the shared
  theme already defines. Cheap and safe to delete; the shared rule takes over.
- **Parallel implementation** — the app implements the same *visuals* under
  **different class names** (`.badge-green` vs the shared `.<ds>-badge--green`,
  `.kpi-tile` vs `.<ds>-kpi-card`). Deleting these means **rewriting every
  screen's widget classes**: large, risky, and zero visual gain.

Don't promise a "quick CSS tidy" before you've looked — that estimate was wrong
in the field case, and the honest answer was to take the token-layer win (§10b)
and **decline** the class-layer churn. Say so explicitly rather than doing a
partial rewrite.

---

## 11. Aligning a toolbar row of mixed controls (dropdowns + native date inputs)

A filter row where some controls carry a caption ("FROM"/"TO") above them and
others don't will look misaligned. Fix it in this order:

1. **Bottom-align the row** — the flex container gets `align-items: flex-end`, so
   captions sit above and every box shares a baseline. **Never insert blank spacer
   captions**: a literal `"\U00A0"` string is not a valid escape in this context,
   so it renders as visible garbage text and reorders the controls (don't "fix" it
   with a working `\00A0` either — space with CSS height instead).
2. **Normalize every control to one height with the same box model** —
   `box-sizing: border-box !important; height: 40px !important; margin: 0 !important`
   on the dropdown container, the inner `<select>`, **and** the date inputs.
   Dropdowns at 36px beside date inputs at 40px is the usual cause.
3. **Native `<input type=date>` has an intrinsic min-height** that ignores
   `height` and renders a couple of px taller. Clamp it:
   `min-height:40px !important; max-height:40px !important; overflow:hidden !important`
   (plus `::-webkit-datetime-edit { padding:0 }` if it still sits proud).
4. **Measure, don't eyeball.** A 2px top offset is visible to a detail-oriented
   client and invisible in a screenshot glance — verify with the pixel-column scan
   in **ui-exactness** (§ Agent enforcement) and require equal tops AND bottoms.

## 12. Fixed-width layout clips on narrow screens — make it fluid

A screen rebuilt at a mockup's fixed desktop width **overflows and clips** on
anything narrower: the classic symptom is a header toolbar whose right-hand
controls (search box, primary "+ New" button) run past the edge with no horizontal
scrollbar.

**Root causes**, all of which have to go: a toolbar/search wrapper with
`flex-shrink: 0` plus a hard `min-width` (e.g. 280px); a `flex-shrink-0` utility on
the title block so it won't yield space; a header/toolbar flex container with **no
`flex-wrap`**, keeping everything on one line; a fixed-px content wrapper; and no
`overflow-x` guard.

**Fix at the shared Theme level** (rule 4 — one Theme, not per-screen patches):

- content container fluid — `width:100%` + padding, never a fixed px;
- `flex-wrap: wrap` on the header row **and** the toolbar, so controls flow onto a
  second line instead of clipping;
- the search flexible — `flex: 1 1 180px` bounded by `min-width`/`max-width`,
  dropping to a full-width row at a small breakpoint — instead of fixed-width;
- `flex-shrink: 1` on the title/left block;
- `overflow-x: hidden` on `body` / main / page wrappers so nothing forces a
  horizontal scroll.

**Verification is the honest part.** The preview MCP is floored at 1920px, so it
cannot show the narrow case at all (see **outsystems-app-build**). Confirm the CSS
landed, confirm no regression at 1920, then hand the narrow-width confirmation to
the user — ask their approximate width and tune the breakpoint. Never call a
responsive fix "verified" off a 1920-only check; say what you could and could not
test.


## 13. Disabled button keeps its enabled styling — add an explicit `:disabled` rule

A gold / primary action button styled by a custom class does **not** change
appearance when the widget's `Enabled` is False — OSUI does not dim a
custom-styled button for you, so it stays fully coloured and *looks clickable
while it is inert*. Field-proven: an `op-btn-place` "Place order" button rendered
solid gold on a Denied order (correctly disabled in the DOM — `<button disabled>`
— but visually identical to enabled), so the user asked "is this supposed to
work?".

**Fix — style the disabled STATE via `:disabled` / `[disabled]` on the button's
class** (in the ONE app Theme, or the screen stylesheet), muting it and blocking
the pointer:

```css
.op-btn-place:disabled, .op-btn-place[disabled] {
  background: #d1d5db;      /* muted grey, not the accent */
  color: #9ca3af;
  border-color: transparent;
  cursor: not-allowed;
  opacity: .7;
}
```

The pseudo-class fires automatically whenever `Enabled` evaluates False, so one
rule covers every occurrence (e.g. "Place order" **and** "Deny" disabled on
non-Queue orders) and every gold button that shares the class. Do NOT gate it
behind an `If` in the widget — style the STATE. The a11y tree already reports
`[disabled]`; only a **screenshot** proves the button now *looks* disabled, so
verify in the preview.

---

## 14. Button labels wrap onto two lines — style the label span, scope the rule

A button whose label wraps ("Open my / dashboard") is usually NOT the button: the
label sits in an inner `<span>` that computed `white-space: pre-wrap; display: block`
at a narrow width, so `white-space:nowrap` on the button changes nothing. Read the
span's computed style, then target it:
`.<page> .btn span { white-space: nowrap !important; display: inline !important; }`.

Scope every button rule to the class it is meant for. A broad
`.<page> button { width:auto }` added for one row shrank an unrelated full-width
sign-in button. After ANY rule on a bare element selector (`button`, `a`, `span`),
re-run the whole parity / screenshot set, not only the check that motivated it.

---

## RTL (Arabic) on ODC Reactive — `dir="rtl"` on `<html>` is NOT enough

Field-proven on a bilingual (EN/AR) portal:

1. **A base style forces `direction: ltr` below `<html>`.** With `<html dir="rtl">` every
   element still computed `direction: ltr`, so flex rows (header, button rows, segmented
   controls) never mirrored — only elements with explicit `[dir="rtl"]` rules moved. Fix:
   `[dir="rtl"] body, [dir="rtl"] #reactContainer, [dir="rtl"] .active-screen { direction: rtl !important; }`
   and use logical properties (`margin-inline-start:auto`, `padding-inline-*`,
   `text-align:start`) instead of left/right.
2. **The platform resets `dir` on screen navigation.** JS that sets `dir` in a button's
   OnClick or a block's OnRender is undone on the next screen. Run it in the shared header
   block's **OnReady** too, and re-apply with `setTimeout(apply, 0)` + `setTimeout(apply, 300)`.
3. **Prove the JS ran.** Mentor-added JavaScript nodes were twice left **unconnected** in
   the flow. Tell: the client variable changes (localStorage shows `…ClientVars$Lang=ar`)
   but `<html lang>` still reads `en-US`. Add a `console.log('marker', value)` and look for it.
4. Mirror fixed chrome explicitly (`[dir="rtl"] .rail{left:auto;right:0}`), and flip
   directional icons with `transform: scaleX(-1)`.

## `ThemeGrid_Width1` / `ThemeGrid_MarginGutter` on root-level containers → float collapse

Widgets Mentor places directly on a screen root (no Layout block) can be given the legacy
grid classes `ThemeGrid_Width1 ThemeGrid_MarginGutter`. On a wrapper container that means
`float` + 1/12 width (~125 px) + a 37 px left margin, and every later sibling wraps around
the float — a whole form collapses into narrow columns. Asking Mentor to re-parent widgets
or strip the classes reported success twice with no DOM change. What landed reliably was
Theme CSS that does not depend on the move:
`.wrapper{position:fixed!important;float:none!important;margin:0!important;…}` plus
`.active-screen:has(> .wrapper){padding-left:<w>px}`. Always verify structure in the live
DOM (classes, computed display/flex-direction, x/width), not in Mentor's summary.
The same move rescues CONTENT Mentor parented in the wrong container: a `position:fixed`
panel (`top:<header>px; left:<rail>px; right:0; bottom:0; overflow:auto`) lays out against
the viewport, so it renders correctly wherever the widget tree actually put it. That holds
only while no ancestor sets `transform`, `filter`, `perspective`, `will-change` on one of
those, or `contain: paint/layout`: any of them makes that ancestor the containing block, and
the panel is placed against it instead. Walk the live ancestors' computed styles before
relying on it.
