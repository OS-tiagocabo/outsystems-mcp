# OutSystems UI Recipes — build these fast in ANY app

> Drop-in recipes for the UI features that recur across ODC builds: reusable
> Blocks, tables (sort + row-navigation), pagination footers, filters, i18n /
> language switching, status badges, dynamic headers, multi-step **Wizards**,
> **DropdownSearch** pre-load on Edit, and Edit-save that actually persists FK
> changes. Each entry is **what to tell Mentor** + the gotcha that makes it land
> the first time. Reuse the recipe instead of rediscovering it.
>
> This skill covers the *feature wiring*. For the base mechanics of a build
> (mentor sessions, publish/verify, data model, seed data) see
> **outsystems-app-build**; for CSS/theming (`Style` vs `CustomStyle`, the
> single-arrow dropdown, block-stylesheet spillover) see **outsystems-css-theming**.

---

## 0. The latency lever — hand Mentor the recipe, don't let it explore

The single biggest time sink in these builds is Mentor **trial-and-erroring an
unknown block API**. A run handed the exact recipe (input names + types +
expressions, scoped to ONE screen) finishes in ~2–9 min; the same feature left to
Mentor to *discover* burned a ~30-min **hung** run. So for any OSUI block with a
non-obvious input, put the input names/types/wiring **in the `mentor_start`
prompt** (the skeletons below are written for pasting).

- **Mentor run hangs (and `mentor_cancel` hangs too).** A run can stall at
  `applyModelApiCode` for 30+ min with no new events (poll with the same cursor;
  if `nextCursor` is unchanged for ~7–10 min it's hung, not thinking).
  `mentor_cancel` may itself sit in `cancelling` indefinitely.
- **Recovery: stay on this session if you can; a new `app_key` is the
  slot-burning fallback, not the default.** While cancel is still in flight, a
  `fresh_context` resume of the SAME session is refused with `run_already_in_flight`
  ("a mentor run is already in flight for this session (runId=…)"). **Wait it out**
  — `mentor_cancel` can sit in `cancelling` for minutes. Failed/cancelled turns
  never commit OML, so the session is still good. Once cancel is terminal,
  `publish_start` will refuse (`not yet terminal-success`) because there is no
  clean success to ship: stay here, run **one trivial clean turn** (theme-comment
  bump — app-build playbook Honest-completion signals), then publish THAT. Open a
  **new `app_key` session only** while `run_already_in_flight` still refuses resume
  AND you cannot wait (cancel hung indefinitely). That burns a scarce slot, drops
  unpublished in-session edits, and reloads last-published OML; the live app is
  unaffected. (Field-proven: `fresh_context` during an ~8 min `cancelling` was
  refused; a new session recovered it — valid, expensive. The cheap path is wait
  → trivial turn on the same session.)
- **Checkpoint by publishing every chunk** — one chunk → one publish → one
  drive-test — so a later hang costs the current chunk, not the whole build, and
  a failing test names the edit that caused it. `no_changes_detected:true` is
  STILL a false alarm every publish — verify by drive-test/reload.
- **Verify the RESULT, not just the flow.** A happy-path click-through misses
  data-correctness bugs (§12). Drive-test the observable *data/state*, not just
  "did the button react".

---

## 1. Reusable / embeddable Block (the ODC unit of UI reuse)

- **Build the screen's main content as a Block** (`<Feature>Block`) from the
  start; the screen just hosts the Block. This satisfies "the main component must
  be embeddable in other apps" for free — a Block IS the ODC reuse unit, so
  another app adds this app as a dependency and drops the Block onto its own
  screen.
- The Block must **own its data** (aggregates + server actions live inside it) and
  **not read screen-level variables**, so it renders standalone in any host.
- **Hardening checklist for real cross-app reuse** (none are blockers for a PoC):
  - Set the Block **visibility = Public** in the module.
  - Give it **input parameters** (`InitialFilter`, `ReadOnly`, `PageSize`,
    `ShowRegisterButton`) and **events** (`OnItemSelected`, `OnItemSaved`) so a
    host presets state and reacts to actions.
  - Consume it elsewhere: **Manage Dependencies → this app → pick the Block →**
    place on a screen, bind params/events.
  - For versioned reuse across many apps, promote the Block + contract into an ODC
    **Library**.
  - A one-screen "host" demo app is the cheapest embedding regression test.
- Prompt skeleton: "Build the `<feature>` UI as a reusable Block `<X>Block`: move
  the aggregate + data actions inside it, keep it independent of screen variables,
  add input params [...] and events [...], place it on `<Screen>`, set it Public."

---

## 2. Table — server-side sort + row navigation + shared nav chrome

- **Server-side sort spanning ALL pages** (base recipe): add a Text var
  `SortColumn` (default `"<Entity>.<PK>"`) + Boolean `SortDescending`, replace the
  aggregate's **static** sort with a single **dynamic** sort whose expression is
  `SortColumn` (append `" DESC"` for descending). The DB sorts **before** paging,
  so the whole filtered set sorts. `OnSortColumn(SortBy)`: same column → flip
  asc/desc; different → asc; always `StartIndex=0` then `RefreshData`. (Full
  mechanics + the icon/link-colour traps live in **outsystems-app-build** §13.)
- **Row → detail/edit navigation — THE WHOLE ROW IS THE TARGET (default).** When a
  table row leads somewhere (a detail screen, an edit modal), the **entire row** is
  clickable, not just a link in one cell. A user aiming at a row expects any part of
  it to work; a single underlined cell is a hit-target the size of a word and reads
  as a bug. Make the row's **`OnClick`** the navigation (`TableRecords` /
  `ListItem` rows expose one — wire it on the row, not on a child) passing the row
  PK; the destination loads via `Get<Entity>Detail(Id)`.
  - **Pure navigation → set the Link's `Destination`, NOT an `OnClick` to a
    screen action.** A `Destination` renders a real `<a href="/Screen">` that
    navigates and is drive-testable in the preview. An `OnClick` that calls a
    screen action renders `<a href="#">` and navigates only if that action
    actually runs a `Navigate` — if it doesn't, the link *looks* wired (it's a
    real anchor with a role+name in the a11y tree) but a click in the preview is
    a silent no-op, and re-snapshotting after the click does not rescue it (the
    `href="#"` anchor is genuinely inert). Field-proven on an order-queue row:
    the row did nothing until it was rebuilt from OnClick-to-action into a Link
    with a real `Destination`. Watch the honest-completion signal — the first
    "set the Destination" mentor run returned `change_applied:false` (narrated,
    not landed); it took an explicit **"clear the OnClick, THEN set the
    Destination"** run to persist.
  - **Every row opening record 1 means the Id isn't the row's own.** The row's
    navigation must pass the CURRENT record of the table's own list
    (`<Aggregate>.List.Current.<Entity>.Id`), bound on the row inside the
    iteration. Bound outside it, or to a first-row variable, every row passes
    the same Id; with no Destination at all the row does nothing. Mentor
    produced both on a first build, so ask for it explicitly ("each row links
    to Detail with that row's Id, via the Link's Destination") and **test a
    row that is not the first**, since row 1 passes either way. If a fix
    doesn't take, ask Mentor to clear the row's OnClick before setting the
    Destination (see above).
  - **DOM event names are RESERVED in Extended Properties — and a `data-*`
    stand-in does nothing.** You cannot add `onclick` (or the other `on*`
    handlers) as an extended attribute. Asked to stop a nested control's click
    from bubbling, mentor silently substituted a made-up `data-stopclick`
    attribute on ~50 elements and reported success: an attribute with **no
    handler behind it**, i.e. pure noise that reads like a solution in the OML.
    Use the widget's own event properties, and if the behaviour genuinely needs
    propagation control, restructure instead — the cheapest fix is usually to
    stop nesting: put each cell's link in the cell and leave the action `Button`
    a **sibling** of the links rather than a child, and there is no bubbling to
    stop in the first place. Whenever mentor invents a `data-*` attribute, treat
    it as unimplemented until you have driven the behaviour.
  - **It must LOOK clickable:** `cursor:pointer` on the row plus a hover
    background — otherwise the affordance is invisible and users still hunt for
    the link. Keep the key-cell styled (bold, brand accent, no underline) as the
    visual anchor, but it is no longer the only hit target.
  - **Keep it keyboard-reachable:** a `div` with an `OnClick` is not focusable, so
    give the row `tabindex="0"` (Extended Properties) and a `role="button"`/`"link"`
    so it can be tabbed to and activated — mouse-only row nav is an accessibility
    regression over the plain link it replaced.
  - **Guard nested controls:** when the row also carries its own buttons (delete,
    a toggle, a dropdown), those must NOT trigger the row navigation — stop the
    event on the child, or the user deletes a record while trying to open it.
  - Style all of it via a CSS **class**, not inline-on-`Style` (see
    outsystems-css-theming).
  - **A "selected row" highlight goes on each cell, not on the row.** The table's
    row-style expression is evaluated once for the whole table, so a class like
    `If(Id = SelectedId, "row-active", "")` on the row tinted EVERY row (Mentor's
    model read showed the right expression). Put the same expression on each
    cell's `Style`/wrapper, or bind it inside the row's own container.
  - **A previous-row comparison must clamp its index.** Group headers or running
    totals that read `List[CurrentRowNumber - 1]` crash on row 0 (index -1) when
    the read isn't guarded. Clamp it — `List[Max(CurrentRowNumber - 1, 0)]` — and
    keep the row-0 guard (`CurrentRowNumber = 0 or …`) for the comparison itself:
    with the clamp alone, row 0 compares with itself, reads as "same group", and
    the first group header never renders.
  - **The exception, and say so when you take it:** a row whose cells lead to
    *different* destinations, or one where a mis-click is expensive (a destructive
    or irreversible action), keeps per-cell links. Everything else gets the whole
    row.
- **Shared nav chrome** — put the top nav + sub-menu in a shared **layout/menu
  Block** every screen inherits. Active entry = a class/`CustomStyle` expression
  on the current screen/tab. You MAY **replace the template's default menu** with
  the design's: edit the shared menu Block's entries/order/styling; don't leave
  the stock OutSystems menu beside the design's nav.
- **Page heading that follows the selected sub-tab** — add a `SelectedTab` Text
  var (default first tab), set it in each tab's OnClick, and drive BOTH the active
  pill (`CustomStyle`) AND the heading text from it. If the tabs aren't wired to
  real content yet, a **static** active pill on the default tab is fine — just keep
  the pill CSS on `CustomStyle` (a dynamic pill on `Style` silently renders
  nothing).
- **Data-driven tab / segment strip — three traps when you replace hardcoded tabs
  with a `List` over a static entity or aggregate:** (1) each per-tab caption must
  be an **Expression** widget, NOT a Text widget — a Text widget whose value is the
  binding renders the *path itself* literally on screen (field-proven: a
  status-segment strip displayed the string
  `GetRequestStatuses.List.Current.RequestStatus.Label` as the button text until
  its caption was changed from a Text widget to an Expression). (2) filter on the
  row's **identifier**, not a label string — a hardcoded label ("In Progress")
  silently matches nothing when the stored value differs ("InProgress") and the
  "All" tab breaks; use `FilterId = 0 OR <Entity>.<Fk>Id = FilterId`. (3) never
  leave a hardcoded `active` class baked into ONE tab's `Style` — a template tab
  shipped as `Style = "…-tab active"` stays highlighted on *every* screen (two tabs
  look active at once); give all tabs the same non-active class and let the dynamic
  active mechanism (OSUI `SetActiveMenuItems`, or your `CustomStyle` active-class
  expression) drive the single highlight so only the current screen's tab is active.

---

## 3. Rows-per-page (page-size) control

- Bind the aggregate's **Max Records** to an Integer var `PageSize` (was a fixed
  literal). A `DropdownSearch` (same component as the filters) bound to a
  `DropdownOption` list (10/12/25/50/100) built by a `GetPageSizeOptions` server
  action in the block's **OnInitialize**. Default 12.
- `OnChangePageSize`: set `PageSize = TextToInteger(Selected.Value)`,
  `StartIndex=0`, `RefreshData`. The pager + record-count summary auto-reflect the
  new size, and it composes with search/filters/sort untouched.
- **A row cap without a pager silently hides data — ship them in the SAME chunk.**
  The moment an aggregate has a `Max Records` (a literal or `PageSize`), every row
  past it is unreachable unless a pager exists. This passes every validation,
  publishes, and looks finished: the table renders its first page and there is
  nothing on screen to say more rows exist. One build shipped a 10-row cap with no
  pager over 17 rows — 7 records invisible to the user, and only a row count
  compared against the table told us. So treat cap + pager + "Showing X–Y of N" as
  one unit of work — this is the "only safe as a whole" exception to the
  one-edit-per-chunk rule (Skill `outsystems-app-generation`, "Chunk size"),
  because the half-shipped state is not incomplete, it is wrong — and when
  drive-testing a table always check the total against
  the rendered row count rather than eyeballing a full-looking first page.

---

## 4. Pagination footer — order + restore the arrows

- **Order per design:** lay the footer as an explicit grid/flex row and place the
  record-count and pager where the design wants (e.g. count **left**, pager
  **right**) — `grid-template-columns:auto 1fr` / `justify-content:space-between`.
- **Blank prev/next buttons?** The OutSystems UI Pagination prev/next can lose
  their glyphs (an icon-library migration leaves empty boxes). Restore by dropping
  a **Phosphor Icon** (`caret-left` / `caret-right`) into the Pagination block's
  prev and next placeholders — same as the sort carets — keeping the buttons'
  navigation behaviour. Drive/verify them in the preview via `.ph-caret-right`
  (clicking it advances a page).
- **…and if the icon-font glyph still won't render, drop the icon and use a
  literal chevron CHARACTER.** The blank prev/next is an **icon-font rendering**
  failure in the Pagination block, and it can survive the fixes above. Two things
  that DID NOT fix it (field-proven this run): (a) confirming the `angle-left`/
  `angle-right` glyph is present, and (b) forcing the icon **`Size`** from
  `FontSize` to an explicit value (`Twotimes`) — the box stayed empty. What
  reliably works: **remove the icon-font Icon and put a literal chevron character
  in an Expression** — `"‹"` (U+2039) for Previous, `"›"` (U+203A) for Next (or
  `◀`/`▶`), styled visibly (≈18px, muted colour), kept as the Pagination block's
  prev/next content so paging behaviour is unchanged. A plain character has no
  icon-font dependency, so it always renders. Watch the honest-completion trap: a
  Mentor `applyModelApiCode` that "sets the arrow icon" reports
  `change_applied:true` with 0 errors while the button still shows blank — only a
  browser screenshot proves the GLYPH is visible; snapshot/assert won't (an empty
  icon has no accessible text). (Field-proven: two icon-based turns left blank
  boxes; the literal-character turn showed ‹ [1][2] › at last.)
- **A bare chevron character is not an accessible name — pair it with hidden
  label text.** Once the icon is gone, `‹` *is* the button's text, so a screen
  reader announces "‹". Add localized visually-hidden text alongside it —
  `wcag-hide-text` (visually hide but accessible, see the styles-and-utilities
  knowledge) wrapping "Previous"/"Next" from the same translation source the rest
  of the screen uses. Then verify BOTH: a screenshot for the glyph AND an
  accessible-name assert for the label. The screenshot-only rule above is about
  the glyph never being provable by snapshot — it is not permission to ship a
  control with no accessible name.
- **Make the accessible-name check a drive-test item, not a good intention.** The
  rule above is easy to agree with and easy to skip: one build shipped an
  icon-only backspace key with no `aria-label` and no `title` at all, and it
  survived a build review because the icon *rendered* — visually there was
  nothing wrong. Enumerate the controls once and assert every one has a name —
  read the **computed accessible name** from an accessibility snapshot, not the
  raw `text` / `aria-label` / `title` fields one at a time: the browser resolves
  those in a precedence order (and folds in `aria-labelledby`, `alt`, and the
  `title` fallback), so checking them individually both misses names that are
  present and passes names that are not. Anything that comes back empty is a
  defect even when the screenshot looks right.
- **An OSUI `Link` with neither text nor icon renders the literal word "link".**
  Not blank, not an error — the string `link`, wired to `href="#"`, which also
  goes nowhere. It reads as a deliberate label in a screenshot and as a real
  control in an accessibility snapshot (`link "link"`), so it passes both a
  glance and a snapshot assert. One build shipped it as a header log-out control.
  When a `Link` is meant to carry an icon, verify the icon widget actually got
  created inside it, and assert the control's accessible name is the one you
  intended — never just that *a* link exists.
- **Bilingual record count:** the built-in count is single-language — hide it
  (`.pagination-counter{display:none !important}`, verify that exact class in the
  widget tree) and show a custom `PaginationSummary` expression instead. Hiding it
  can break the footer flex — re-lay it as the explicit grid/flex row above.

---

## 5. Filters & search — and the filter-dropdown "repeated label / stray 0" trap

- **Base filters + text search over one aggregate:** one screen var per filter
  (`Filter<Attr>` Text, `FilterStatus` default `"All"`), a distinct-value
  aggregate per text filter (grouped by that attribute, sorted asc, one row per
  value), AND-combined filter rows
  (`Filter<Attr>="" OR <Entity>.<Attr>=Filter<Attr>`), each dropdown OnChange
  refreshes + resets to page 1. (Full recipe in **outsystems-app-build** §6.)
- **The custom-list-dropdown trap** — symptom: opening a filter shows the SAME
  caption for every option and/or a stray "0" at rest. Two independent causes;
  the reliable fix is to stop fighting a hand-rolled dropdown:
  1. A CUSTOM list/repeater dropdown often binds option text to a screen
     variable/child-expression instead of the row's own `.Label`, so every option
     renders the same text → replace it with the **native reactive `Dropdown`**
     widget (Source list, `OptionsText`=row label, `OptionsValue`=row id), which
     renders per-row labels correctly.
  2. The reactive Dropdown's **`Prompt` property does NOT render as a placeholder
     option** in some ODC builds — the empty value shows as the raw value "0".
     Don't rely on `Prompt`: put a real **data "all-row"** as the FIRST list item
     (`Value` = the variable's default — `NullIdentifier()` for Identifier vars,
     `0`/`""` to match; `Label` = the "All …" caption, language-aware). The
     variable default then equals the all-row's value, so at rest the all-row is
     selected and the caption shows the words.
  3. Finally **clear `EmptyValue`** (leave it unset) or you get a phantom "0"
     option *in addition to* the all-row.
  - Net recipe: native `Dropdown` + data all-row (value=default, label=caption) +
    no `EmptyValue` + `OptionsText` bound to each row's own label. The aggregate
    filter checks the variable (`filter = default OR match`), so the all-row = no
    filter. Make option labels language-aware with the SAME expression the
    table/badges use (§6), else the dropdown shows one language while the table
    shows another. (The extra chevron this widget can grow is a CSS issue — see
    **outsystems-css-theming**.)
  - **Field note — the empty-option TEXT edit lies.** Setting the Dropdown's
    empty-option / `Prompt` **text** (e.g. to "All statuses") via Mentor can report
    `change_applied:true` with 0 errors, yet the running `<select>` still shows the
    raw value ("0"). The text edit does not render. Only the **data all-row** above
    (a real first option whose value equals the variable default) reliably shows the
    caption at rest. Confirmed the hard way: two empty-option-text turns landed in
    OML but still rendered "0"; rebinding the dropdown to a list with an "All …"
    all-row fixed it. Keep the widget this recipe prescribes — the platform
    `Dropdown` above (or OSUI `DropdownSearch` when you need search); the point is
    that the fix is the **data all-row**, not the widget swap, and not a
    hand-rolled `<select>`.
  - **No empty first option = the filter loads pre-selected.** A native
    `Dropdown` with no all-row writes its FIRST option into the bound variable on
    render, so a list filter starts filtered (1 of 8 rows) and "clear filters"
    snaps straight back to it; guards in `OnChange` don't help. The all-row above
    (value `""` for a Text var) is also the fix for this. Mentor may report
    `DropdownSearch` as unavailable in an app and drift into a hand-rolled
    `<select>` + JavaScript — cancel that turn and ask for the all-row.
  - **Rebuild a dropdown's option list, never append to it.** An option list
    appended to in an `OnAfterFetch` grows a copy of every option on each refresh
    (a search or filter change re-fetches). Bind the dropdown to the aggregate
    directly **only when that source already includes the all-row**; a
    distinct-value aggregate does not, so binding to it drops the empty option and
    brings back the pre-selected filter above. Otherwise build the list: when the
    options come from a screen aggregate, build them in that aggregate's
    `OnAfterFetch` (`OnInitialize` runs before the fetch, so the aggregate is
    still empty there): **clear the list first** (`ListClear`), append the
    all-row first, then append the fetched values. `OnInitialize` is fine only for static
    options that don't depend on fetched data.

### Live filter lags one keystroke — the non-reactive-aggregate fix

- **Symptom:** typing in a list's search/filter narrows the rows **one keystroke
  behind** (the list matches what you typed *before* the last character). Two ODC
  facts combine to cause it: screen **aggregates are not reactive** (they only
  re-run on an explicit `RefreshData`), and a native **`Input` commits its bound
  variable only *after* `OnChange` fires** — so an `OnChange → RefreshData` handler
  refreshes with the *previous* value.
- **Fix (any one; the last is the most robust):**
  - Read the input's **live DOM value** into the bound variable *before*
    `RefreshData` in the handler.
  - Use the OSUI **`Search`** pattern instead of a bare `Input` + manual refresh.
  - **Reference the filter variable inside the aggregate's filter** so the aggregate
    is reactive to it and re-runs as the value changes — it then narrows on the
    **first** keystroke. Keep the Search button, scope toggles and category
    dropdowns working alongside.
- **Verify by typing ONE character** and asserting the row set narrowed on *that*
  character — not after the next one. Audit every list screen (each is wired
  separately, so the lag can hide on the ones you didn't drive).

---

## 6. Language switcher — localize EVERYTHING (titles are the #1 miss)

- **Mechanism:** a `Client.UILanguage` check, one language default; every
  user-facing Text = `If(Client.UILanguage="EN","<EN>","<other>")`. It re-renders
  instantly (no reload) and persists across a full reload. Localize chrome +
  **validation messages + toasts + the pagination count** (not just labels) — the
  common inverse bug is success toasts staying in only one language.
- **Commonly-missed surfaces — localize these too:**
  - **Page titles / headings AND breadcrumbs.** THE most-missed spot: everything
    else switches while the H1 stays static. Every screen's heading + breadcrumb
    segment must use the `Client.UILanguage` expression.
  - **Remove dual-language sub-labels.** A common pre-i18n design shows a heading
    in one language + a permanent second-language subtitle beside it. Once the
    heading localizes, that subtitle is a redundant duplicate — **remove it** so
    only ONE language shows at a time. (Don't strip the default language
    generally; only remove the redundant *simultaneous* duplicate.)
  - The DropdownSearch "All" prompt and the "Total N items" wrapper (they live
    inside blocks / among static text).
- **Audit ALL screens, not just the main one.** After localizing the primary
  screen, walk every other screen (list, detail, stubs) and confirm its
  heading/breadcrumb switches — they're built separately, so each can be missed.
  Drive the switch on each.
- **Translate CHROME only, never stored DATA.** Titles, section/modal titles,
  column headers, button/field labels, helper text, and derived labels (the
  status badge) switch; entity cell values stay in their original language.
- Title-fix prompt skeleton: "Make `<Screen>`'s page heading + breadcrumb localize
  via `Client.UILanguage` ('<a>' / '<b>'); remove the redundant always-one-language
  subtitle beside the heading. Mirror the `<other screen>` heading fix."

---

## 7. Status badge from a boolean

- Replace a Y/N expression cell with a **pill Container** whose CSS **class**
  switches on the boolean: `badge-active` (e.g. green "Active") / `badge-inactive`
  (grey "Inactive"). The screen stylesheet frequently already HAS these classes
  (`badge-*`, `seg-btn`, …) — reuse them; put the switch on a class expression, not
  inline-on-`Style`. Localize the badge text with the same `Client.UILanguage`
  expression as the rest of the chrome.

---

## 8. Dynamic header (real signed-in user name + role)

- **This is a DEFAULT, not an opt-in.** Most apps ship login/logout (wired, not
  activated — see outsystems-app-build §14) and, once signed in, the header
  shows the user's **name + role**. Build it unless the user explicitly says
  the app has no sign-in.
- Shared `TopNav` block: a `GetCurrentUser` aggregate (`User.Id = GetUserId()`),
  show `Name` (fallback `Username`) + role `If(CheckAdminRole(),"Admin","User")`.
  Logged-out shows the login link.
- **Avatar = initials from the user name — the first letter of the FIRST word +
  the first letter of the LAST word, uppercased** ("Maria Silva" → "MS"; a
  single-word name → its first two letters). Do NOT use "first + last letter of
  the whole string" (`Substr(DisplayName,0,1) + Substr(DisplayName,Length-1,1)`)
  — that yields "Ma" for "Maria Silva" (field-proven: it rendered "UR" for the
  fallback "Unknown user"). Compute over a `DisplayName` local var so the
  `Username` fallback is baked in (`DisplayName = If(Name <> "", Name, Username)`),
  then `ToUpper(Substr(FirstWord, 0, 1) + Substr(LastWord, 0, 1))` where
  `FirstWord` is the text before the first space and `LastWord` the text after the
  last space (no space → the first two characters). Gotcha: the OSUI
  `UserAvatar` block (`Common/UserInfo`) derives initials ITSELF from its
  `Name` argument (word initials) and uses `Name` as the image alt text — so
  do NOT bind the precomputed two-letter string as `Name` (unspecified
  rendering + broken alt text). Keep the real name on `UserAvatar.Name` and
  accept its default initials; when the design specifically wants the
  first+last-letter form, render the expression in a small styled disc (an
  Expression inside a rounded Container) in place of the block's initials —
  and drive-check what actually renders in the preview.
- **Do NOT** use `GetUser(GetUserId()).User.Name` in a build-time expression — it
  fails **deploy** validation `OS-DPL-50205` (a `GetValidationMessages`-invisible,
  deterministic deploy-time trap; see outsystems-app-build §12). Use the aggregate.
- **Two sign-in cases on an Anonymous (wired-not-activated) app — choose the name
  source by which one you have.** (a) A **real platform / SSO login** (the user
  signs in through the tenant identity provider, or `(System) Login` succeeds)
  DOES create a session: `GetUserId()` is non-null and the `User` aggregate above
  resolves — *even though every screen stays Anonymous*. Read the name from that
  aggregate. Keying the header off a client var the SSO flow never sets is what
  shows "Unknown user" (avatar "UR") right after a real login — field-proven, and
  fixed by reading `User.Name` on `GetUserId()`. (b) A **custom / demo roster
  login** that does NOT call `(System) Login` leaves `GetUserId()` null, so
  `User.Id = GetUserId()` matches nothing and the header stays blank — for THAT
  case only, capture the name into a CLIENT VARIABLE at login and read THAT. Have the
  login action write the display name (and role) into a **client variable** and
  drive the header + initials disc off that client var instead of the aggregate
  — that is the pattern that makes initials appear before activation. Add a
  **demo login** (e.g. a fixed `"demo"` password that sets the client var) so the
  signed-in header is drive-testable in the preview without activating auth;
  remove the demo login before activation. Field-proven: a `GetUserId()`
  aggregate header showed no initials after sign-in until it was rebuilt on the
  client-var-at-login pattern.

---

## 9. OSUI `Wizard` + `WizardItem` — the multi-step form

- **They exist in `OutSystemsUI`** — they ship with the OutSystems UI
  dependency every template app already references (no tenant lookup needed).
  Prefer them over a hand-built progress bar (OutSystems UI is the preferred
  source of blocks).
- **`Wizard` is a pure LAYOUT container — it has NO active-step input.** You do NOT
  tell the Wizard "current step = 3". Instead:
  - Put N `WizardItem` blocks inside the Wizard's Content placeholder, one per
    step, each with `Label` = the step title and `UseTopLabel = True`.
  - Drive each `WizardItem`'s **`Status`** input (type `OutSystemsUI.Steps`
    identifier) from your own `CurrentStep` integer:
    `Status = If(CurrentStep > N, Entities.Steps.Past, If(CurrentStep = N, Entities.Steps.Active, Entities.Steps.Next))`
  - The step **content** is separate: keep `Step1..StepN` containers *below* the
    Wizard, each `Visible = CurrentStep = N`. Back/Continue buttons call a
    `GoToStep(n)` action that just sets `CurrentStep`. The Wizard block only
    renders the numbered header/progress.
- Renders in the a11y tree as a `tablist` of `tab`s — assert steps with `role=tab`.
- Structure is identical for Create and Edit — build Create first, verify, then
  tell Mentor "mirror `Create<Entity>` exactly on `<EditScreen>`".

---

## 10. DropdownSearch pre-load on an EDIT screen (`StartingSelection`) — 3-part fix

The OSUI `DropdownSearch` (VirtualSelect / `vscomp`) does NOT pre-select from a
scalar Id. Pre-selecting the current value on an Edit screen has **three**
independent traps — fix all three or the picker shows its placeholder:

1. **Input name/type:** the pre-selection input is **`StartingSelection`**, type
   **`DropdownOption List`** (structure `OutSystemsUI.DropdownOption`, fields
   `Value`(Text) + `Label`(Text)). Build it inline from the source row:
   `<Aggregate>.List → { Value: LongIntegerToText(Id), Label: <display text> }`.
   The `Value` must equal an `OptionsList` option's `Value` or it won't match.
2. **Read-once-at-init:** `StartingSelection` is read only when the block
   **mounts**. If its data arrives later the picker stays empty. **Fix: render the
   picker only after its data is fetched** — wrap it in
   `If(<Aggregate>.IsDataFetched, <DropdownSearch>, <disabled placeholder>)`.
3. **Chicken-and-egg filter:** do NOT filter the pre-selection aggregate by a
   **local variable set inside an OnAfterFetch** — that aggregate fetches once
   while the local var is still empty and never re-fetches → 0 rows. **Filter by
   the reactive SCREEN INPUT PARAM instead**, joining through the parent:
   `<Child> JOIN <Parent> on <Parent>.<ChildFk>=<Child>.Id, FILTER <Parent>.Id = <PkParam>`
   (MaxRecords 1, inner join so a null FK → 0 rows). Input params are always
   available, so the aggregate returns the row reactively.

- **Summary/label rows: bind REACTIVELY, don't copy in an action.** A summary
  panel should bind each row directly to `<Aggregate>.List.Current.<attr>` (guard
  `IsDataFetched and Length>0`), NOT to label vars set in OnAfterFetch (same
  chicken-and-egg). Trade-off: a reactive summary reflects *saved* data, so it
  won't live-update as the user edits a picker mid-form (usually fine on Edit). For
  live-update too, also set the label var in each picker's OnChanged and show
  `If(labelvar<>"", labelvar, aggregateValue)`.

---

## 11. Edit-save that silently drops FK/dropdown changes — the `Update<Entity>(Rec)` fix

- **Symptom:** on an Edit form, scalar text/number fields persist but **dropdown
  (FK) changes don't**, and *unchanged* FKs appear "preserved".
- **Root cause:** the Save action only updates scalar columns (e.g. a bespoke
  `Update<Entity>Fields`) and never writes the FKs. The dropdown OnChanged handlers
  may be perfectly correct
  (`Rec.FkId = LongIntegerToIdentifier(TextToLongInteger(SelectedOption.Current.Value))`)
  — the bug is downstream.
- **Fix:** Save must call the entity's **`Update<Entity>(Rec)`** with the FULL
  record (all FKs), then add the scalar update after if one exists.
- **Verify by change-a-dropdown → save → reload the EDIT form** — presence on a
  detail screen is not proof (next).

### "The detail screen doesn't reflect my save" — check it reads a DIFFERENT field
Before assuming a save bug: a detail/read screen may show a value sourced from a
*different* attribute than the one you edited (e.g. a detail's "billing address"
rendering the client/correspondence address, not `<Entity>.BillingAddressId`). It
never changes across edits — looks like a broken save, but the Edit screen's own
picker (reading the field you wrote) is the correct oracle. **Verify a save on the
screen that reads the same field you wrote**, not only on a detail screen.

---

## 12. Data-correctness gotchas a happy-path click-through misses

Always drive-test the observable data/state, not just "did the button react":

- **Create action fed an EMPTY record literal `{}`.** Mentor can wire a
  create-from-form modal whose `Create<Entity>` Source is an unassigned `{}` → the
  row inserts with ALL defaults (Integer=0, Date=1900-01-01, empty FKs/text) even
  though the success toast interpolates the entered value (the toast reads the
  input var; the insert used the empty record). **Fix:** assign a record var
  explicitly (`.Field = <inputVar>`, `EntryDate = CurrDate()`, defaults for the
  rest) and pass THAT as Source. **Test:** after create, read the new ROW's values
  in the table — not just that a row appeared / a toast showed.
- **Popup action buttons silently missing.** A native `Popup` can open with its
  fields but NO Create/Cancel buttons (only the ×), even when the summary claims it
  added them — they weren't placed in the popup's visible content container.
  **Test:** the a11y snapshot of the open dialog must list the Create/Cancel
  buttons. Put the footer buttons inside the SAME content card as the fields.
- **A leftover client-side JS action overriding a reactive-bound class.** Symptom:
  a highlight / active-state (e.g. a language pill) is wrong ONLY on first load and
  "self-heals" after any click. Cause: an OnReady `JavaScript` action re-setting
  the class from `localStorage` (defaulting to one value) regardless of the real
  flag (`Client.UILanguage`). **Fix:** delete the JS override and drive the class
  purely from the reactive flag the rest of the UI uses. **Tell:** "correct after a
  click, wrong on load" → suspect an OnReady/JS override, not the binding.

---

## 13. Reusable `mentor_start` skeletons

**Rebuild a form as an OSUI Wizard:**
> On `<Screen>`, replace the hand-built progress bar with the OutSystemsUI
> **`Wizard`** block. Inside its Content add N **`WizardItem`** blocks (Labels:
> <...>), each `UseTopLabel = True` and `Status = If(CurrentStep>K,
> Entities.Steps.Past, If(CurrentStep=K, Entities.Steps.Active,
> Entities.Steps.Next))`. Keep the existing Step1..StepN containers below
> (Visible = CurrentStep=K) and Back/Continue→GoToStep. The Wizard is layout-only
> (no active-step input). Keep all field wiring + summary panel.
> GetValidationMessages = 0 errors. Screens stay Anonymous.

**Pre-load DropdownSearch selections on an Edit screen:**
> On `<EditScreen>`, make each DropdownSearch show the record's current value. For
> each picker: (1) an aggregate filtered by the **`<PkParam>`** input via inner
> join to `<Parent>` (MaxRecords 1), NOT by a local var; (2) set the picker's
> **`StartingSelection`** (DropdownOption List) inline from that aggregate
> `{Value: LongIntegerToText(Id), Label: <text>}`; (3) wrap the picker in
> `If(<Aggregate>.IsDataFetched, picker, disabled placeholder)`. Bind summary rows
> directly to `<Aggregate>.List.Current` (guard `IsDataFetched and Length>0`).
> Ensure Save calls `Update<Entity>(Rec)` so FK changes persist. Don't touch the
> Create screen. 0 validation errors; screens stay Anonymous.

---

## 14. Breadcrumbs — the real OSUI `Breadcrumbs` pattern (not hand-rolled)

- Use the OSUI **`Breadcrumbs`** pattern, never hand-rolled markup. Non-current
  segments are **clickable links that navigate** to the page they represent (e.g.
  "<List>" → the list screen); the current page is **plain emphasized text**, not a
  link. Links carry **no underline** (that's the base OSUI `a{}` link-colour rule —
  see **outsystems-css-theming**).
- **Only detail-level screens need a breadcrumb** (a list → detail trail). Don't put
  one on a top-level list or dashboard screen.
- **Audit app-wide for stray duplicates.** A breadcrumb accidentally added on more
  than one surface — or a leftover hand-rolled one sitting beside the OSUI pattern —
  renders as a doubled trail. Walk every screen and remove the extras so each screen
  carries **at most one**.
- **Verify** the non-current segment actually navigates (drive-click it) and that the
  current segment is not a link.

---

## 15. Export a list — mirror the filters, and the `Max. Records = "0"` trap

**"The Export button does nothing" — no download, no server error.** Two root
causes, both silent: the button's `OnClick` is bound to an empty **NoOp client
action** (Start→End, no logic), or the server action builds the bytes but there is
**no client `Download` node** to hand them to the browser. Wire `OnClick` → client
action → `Download(FileContent, FileName)` with a date-stamped name, adding
`BinaryData` + `FileName` outputs to the server action if they're missing. Then
verify the file **off disk** (**outsystems-auth-and-deploy** §8) — a wiring check
is not a PASS. Check the CSV's *content* too: a 5-column dump missing
ClientName/Account isn't useful; export the columns users actually see in the list.

An Export button beside a filtered list is expected to export **what the screen is
showing**, across all pages:

- Pass the screen's **live filter variables** into the export action, and give the
  export's aggregate the **identical filter logic** as the on-screen list aggregate
  (status tab, product, owner scope, search text) — not a re-derivation. Hardcoded
  inputs (`product = ""`) are why a CSV ignores the screen.
- Leave the export aggregate's **`Max. Records` BLANK**. In a **server-action**
  aggregate the literal `"0"` means *fetch zero rows* (the platform returns a single
  near-empty row) — it does **not** mean unlimited. The symptom is an export that
  always writes exactly **one** row whose content still changes with the filters.

Full recipe, the `DIAG_ROWCOUNT=` probe that localises it in one round-trip, and how
to verify the downloaded file off disk: **outsystems-auth-and-deploy** §5–8.

---

## 16. A counter that never moves is a hardcoded mockup literal

A build reproduced from a Figma/design mockup often ships **sample numbers that
were never bound to a query**. The tell: a header KPI or counter pill reading an
oddly specific value ("209,431 total") while the real table holds 219 rows — and
the number **doesn't change** when you filter or add/remove records.

- **Detect** by sweeping every stat / counter / badge / KPI after a mockup-based
  build and asking "does it match the real data, and does it move when the data
  moves?" Cross-check against a ground truth you trust: a status-tab total, the
  "Showing 1–N of M" footer, or the export row count.
- **Fix** by rebinding the widget expression to a real aggregate — e.g.
  `LongIntegerToText(GetCountAll.Count) + " total"` over a no-filter Count
  aggregate already on the screen. Thousands separators are fine; the VALUE must
  equal the true count and track it live.
- A mockup literal is to a counter what lorem is to a table.

---

## 17. Honest, fully-wired navigation — every control goes somewhere real

A build reproduced from a design/launchpad ships a full grid of nav tabs, domain
tiles, sub-tabs, and action buttons — and most of them lead **nowhere**. Users
read a dead control as a broken app, not an unbuilt feature. The rule: **every
visible control either navigates to a real screen or is honestly marked
not-built — nothing is a silent no-op.** Four moves make navigation trustworthy:

- **Reconcile the control set against the SPECS, not the generic launchpad.**
  Before wiring, list what the specs (screens doc, user journeys, business rules)
  actually define as reachable areas, and cut controls the design invented that
  the specs don't back. A top-nav tab or domain entry that maps to no spec area
  is noise — remove it or demote it (translucent, see below). Don't wire a
  control just because the mockup drew it.
- **Wire EVERY surviving control — real screen or shared placeholder.** For an
  area the specs require but you haven't built yet, don't leave the button inert:
  point it at a shared **`NotImplemented`** placeholder screen that takes the
  area name as an input param and shows "*&lt;Area&gt; — not implemented yet*"
  plus a **Back** link. One placeholder screen serves every unbuilt area (pass a
  different param). Now every click lands somewhere and the app never feels
  broken; the report/plan still tracks the area as a real gap.
- **Design-only controls become TRANSLUCENT, not clickable.** When the user
  wants a control kept for visual completeness but it genuinely has no
  destination (e.g. extra domains in a switcher list that the specs don't
  cover), render it **translucent / disabled** (reduced opacity, no pointer
  cursor, no OnClick) so it reads as "shown for context, not active" rather than
  a live button that does nothing. Reserve the placeholder-screen route for
  controls that SHOULD eventually work; use translucency for controls that are
  purely illustrative.
- **A single-page detail/config screen does NOT get a sub-tab strip that links
  to a placeholder.** If a screen's "sub-tabs" are really just on-page sections
  (all content already visible on one page), a tab strip whose entries navigate
  away — or to a NotImplemented screen — is actively misleading. Remove the strip
  and let the sections stand, or wire each tab to the real section. A tab that
  looks like navigation but isn't is worse than no tab.

**Action buttons are navigation too — a queue action must mutate the field the
aggregate FILTERS on.** An Approve / Reject / Complete / Route button that
"looks wired" but leaves the list unchanged is the same dead-control problem in
disguise. The button must change the **exact attribute the list aggregate filters
on** (not a sibling status field), then `RefreshData` — otherwise the row stays
in the queue and the action is a silent no-op. Field-proven: an "Approve fiat"
button set a dossier to `Active` (already `Active`) while the pending queue
filtered on a *different* flag, so approving changed nothing on screen; the fix
was a dedicated `PendingFiatApproval` boolean the queue actually filters on,
cleared by the approve action. After any queue-mutating action, drive it in the
preview and assert the row **leaves** the list.

- **Strip the leftover hyperlink colour from wired nav.** Once a nav entry is a
  real `<a href>`, the theme's anchor colour lands on it and it reads as an
  underlined gold/blue link, not a menu item. De-style nav anchors (and any
  content links that inherit it) via the Theme — see outsystems-css-theming §8.

---
## 18. Runtime bulk import from Excel — the end-user Upload screen

**This section is the canonical definition of how the import screen is built** — where the
two files disagree, this one wins. It is not the only copy: the legacy-modernization plugin's orchestrator,
planner and reporter roles carry short summaries so the plan items and the report can be
written without loading the recipe. **Those summaries have to stay aligned**, so a change here
means checking them — the last drift left the prompts asking for three outcome counts while
this section required four.

### The shape, in one place

```
ImportData                    ONE screen for the whole app, MainFlow, gated,
                              reached from the app's TOP MENU (single entry)
  ├─ Dropdown  SelectedEntity → Text screen local, default ""
  │             options ← EntityOptions (screen local list, filled in OnReady)
  │
  │   everything below is HIDDEN until SelectedEntity <> ""
  │
  │
  │   THREE Text nodes — the ONLY guidance text on the screen (no "How to use
  │   this page" title, no other preamble; field-specific details — Boolean values,
  │   date format, self-reference behaviour — go in the rejection reason, never a
  │   fourth line), every one MANDATORY, in THIS order. The first line states what
  │   BOTH modes do, because Replace is the default and deletes rows the file omits:
  │   a user who reads only this screen has to learn that here, not from the
  │   confirmation that appears once they have already pressed Import:
  ├─ Text      "Replace all data: this file becomes the whole table — anything
  │             not in it is deleted. Add and update: nothing is deleted. In
  │             both modes, leave the Id blank to add a record or fill in an
  │             existing Id to update that one. Always start from one of this
  │             page's downloads and do not add, remove or reorder its columns."
  ├─ Text      "Reference columns need the Id number, not the name — copy it
  │             from that entity's Download current data."
  ├─ Text      "Accepted files: .xls, .xlsx or .xlsb, up to 10 MB."
  ├─ "Download template"     → Switch(SelectedEntity) → GetTemplate<Entity>
  │                            → Download     (headers only, Id column blank)
  ├─ "Download current data" → Switch(SelectedEntity) → ExportCurrent<Entity>
  │                            → Download  (every row; own Id AND every
  │                              reference Id filled, as NUMBERS)
  │                            ← NO JOINS, no display names. Same columns in
  │                              the same order as the template.
  ├─ Upload widget  → UploadedFile (Binary Data local)
  │                 → UploadedFileName (Text local)
  │                 accept=".xls,.xlsx,.xlsb"  ← a PICKER HINT. NOT a check.
  ├─ Mode      ImportMode → Text screen local, "Replace" (the default) or
  │             "AddUpdate" — a VISIBLE control next to Import, never a hidden
  │             default, because one of the two deletes data
  ├─ "Import"  CLIENT action, in this order — NOT a bare call to the server:
  │    1. empty check — UploadedFile null or zero length
  │    2. extension check on UploadedFileName (whitelist xls / xlsx / xlsb)
  │    3. size check on UploadedFile against the pinned byte constant
  │       ANY failure → set ErrorMessage to the exact string, HasRun = False,
  │                        clear the five counts + Rejections, and END the action.
  │                        NO fallthrough to steps 4 and 5.
  │    4. ImportMode = "AddUpdate" → Switch(SelectedEntity) →
  │       Import<Entity>FromExcel (SERVER), Mode "AddUpdate", the three
  │       Confirmed inputs 0 → show the results, END. No confirmation: this
  │       mode never deletes.
  │    5. ImportMode = "Replace" → Switch(SelectedEntity) →
  │       Preview<Entity>Import (SERVER, validate-only, writes NOTHING)
  │         ErrorMessage <> ""  → the refusal path above, END
  │         RowsRejected > 0    → show RowsRead / RowsRejected + Rejections,
  │                               Created / Updated / Deleted all 0, END —
  │                               nothing will be written, so nothing to confirm
  │         otherwise           → ToCreate / ToUpdate / ToDelete into
  │                               PendingCreate / PendingUpdate / PendingDelete,
  │                               ShowConfirm = True
  ├─ Popup     ConfirmReplace, open while ShowConfirm — the EXACT numbers the
  │             preview returned, never an estimate:
  │             "Replace all <Entity> data? <PendingDelete> existing rows will
  │             be deleted, <PendingCreate> created and <PendingUpdate>
  │             updated. This cannot be undone."
  │             PendingUpdate = 0 AND PendingDelete > 0 → prefix "Every existing
  │             <Entity> row will be removed — nothing in this file matches one."
  │             (the blank template filled with new rows, uploaded in Replace)
  │    Cancel  → ShowConfirm = False, clear the Pending counts, nothing sent
  │    Confirm → "CommitReplace" CLIENT action → Switch(SelectedEntity) →
  │              Import<Entity>FromExcel (SERVER), Mode "Replace", Pending
  │              counts as ConfirmedCreate / ConfirmedUpdate / ConfirmedDelete
  │              → ShowConfirm = False, show the results (a changed-data
  │              refusal lands in ErrorMessage like any other)
  └─ Results   → screen locals HasRun (Boolean), RowsRead / RowsCreated /
                  RowsUpdated / RowsDeleted / RowsRejected (Integer), Rejections
                  (ImportRejection List), ErrorMessage (Text), PendingCreate /
                  PendingUpdate / PendingDelete (Integer), ShowConfirm (Boolean)
                  — ALL cleared on entity change, on a new file or mode, AND on
                  every refusal

Validate<Entity>Import(FileContent Binary, FileName Text, Mode Text)
  ← SERVER only, never called from the client. The ONE validation: the preview
    and the commit both call it, so they cannot disagree about a row.
    Writes NOTHING and deletes NOTHING, in either mode.
  → RowsRead, ToCreate, ToUpdate, ToDelete, RowsRejected (Integer)
  → Rejections (ImportRejection List)      ← named Structure, see below
  → ErrorMessage (Text)                    ← file-level refusal; empty when fine
  → ValidRows (<Entity> List)              ← null Id = create, else update
  → DeleteOrder (<Entity> Identifier List) ← Replace only, child-first

  0.  MODE CHECK — Mode must be exactly "Replace" or "AddUpdate". Anything
      else → ErrorMessage "Unsupported import mode '<Mode>' — choose Replace
      all data or Add and update.", no parse, nothing written. Mode arrives
      from the client, so an unknown token must never fall through to either
      branch below.
  1a. empty check on FileContent (null or zero length) AND extension check on
      FileName AND size check on FileContent — THE SAME
      whitelist and THE SAME byte cap, repeated HERE. The client is not a trust
      boundary: a direct caller skips it, and if the tenant request limit is
      higher than the cap it can slip an oversized file past. This server copy is
      the gate for all three — fail → return the matching file-level message, no
      parse. The empty check belongs HERE, before the parse: a zero-byte file that
      reaches 1b comes back IsReadable = False and reports "couldn't read that
      sheet" — the wrong message for a file that is simply empty.
  1b. ParseImportSheet<Entity>(FileContent) → StagedRows, IsReadable
      ← its OWN server action with its OWN All Exceptions handler, because
        exception handlers are per-FLOW, not per-node.
  1c. if not IsReadable  → return the unparseable-sheet message
  1d. if StagedRows is empty → empty-sheet message, in BOTH modes. In Replace
      this is also what stops a headers-only file (the blank template uploaded
      as-is) from emptying the table: an empty Replace is refused, never run.
  2.  VALIDATE-ALL pass — ForEach staged row, collecting faults. SeenIds
      (Identifier → sheet row) starts empty.
        ← COLLECT the row's faults into one Reasons list, do NOT bail on the
          first. A row that fails conversion AND has a bad foreign key must
          report both; see "Reasons must name the field that failed".
        Convert<Entity>Row     → IsValid, typed record, Reasons (Text List)
                                 ← converts EVERY cell through a per-cell
                                   Try<Type> helper, so one bad cell never hides
                                   the next; see "Converting Text safely"
        if invalid             → add its Reasons to this row's Reasons, and skip
                                 only the checks that need the converted value
        FK CHECK, per foreign key on the entity:
          blank + optional     → no reference, carry on
          blank + mandatory    → add "<Label> is required"
          not a whole number   → add "<Label> must be a whole number"
          no such row EXISTS   → add "<Label> <n> does not exist"
          ← this lookup is NOT optional; see "Foreign keys"
        Id FILLED + NO such row→ add "No record with Id <n> exists"
        Id FILLED + in SeenIds → add "Id <n> appears more than once in this
                                 file — first on row <r>". The first
                                 occurrence stands; every later one is rejected,
                                 so no record is written twice
        Id FILLED              → add it to SeenIds with this sheet row
        UNIQUE CHECK, per unique index on the entity (see "Unique indexes —
        the commit order decides what can collide"):
          key already used by an earlier row of this file → add "<Label>
                                 '<v>' is already used on row <r> of this file"
          blank Id, AddUpdate, an existing row holds the key → add "<Label>
                                 '<v>' already exists (Id <m>)"
          filled Id, a DIFFERENT existing row holds the key → add "<Label>
                                 '<v>' still belongs to Id <m> when this row is
                                 updated — change it in a separate import once
                                 Id <m> no longer holds it"
        if Reasons is non-empty→ append ONE rejection joining them with "; ",
                                 count it rejected, next row
        otherwise              → append the typed record to ValidRows;
                                 blank Id → ToCreate + 1, filled → ToUpdate + 1
  3.  DELETION PLAN — Replace mode only, and only when RowsRejected = 0:
        DeleteSet = every existing <Entity> Id NOT in SeenIds; ToDelete = its size
        ORPHAN CHECK — refuse, never cascade ("Replace must refuse rather
        than cascade"). Either case → ErrorMessage naming the blocking row:
          a row of ANOTHER entity references a DeleteSet Id
          a ValidRows self-reference names a DeleteSet Id
        DELETE ORDER — self-references AMONG the DeleteSet rows:
          repeat: take every DeleteSet row that no other remaining DeleteSet
          row references (a row pointing at itself does not count), append
          them to DeleteOrder, drop them from the set
          rows remain and none can be taken → a CYCLE → ErrorMessage naming
          them ("Rows being deleted can reference each other")
  4.  return the counts, Rejections, ErrorMessage, ValidRows, DeleteOrder

Preview<Entity>Import(FileContent Binary, FileName Text)
  ← the Replace preflight the client calls before it confirms.
  → RowsRead, ToCreate, ToUpdate, ToDelete, RowsRejected (Integer)
  → Rejections (ImportRejection List), ErrorMessage (Text)
  1.  Validate<Entity>Import(FileContent, FileName, "Replace") and return its
      counts, Rejections and ErrorMessage — never ValidRows or DeleteOrder.
      NOTHING is written or deleted.

Import<Entity>FromExcel(FileContent Binary, FileName Text, Mode Text,
                        ConfirmedCreate / ConfirmedUpdate / ConfirmedDelete Integer)
  ← the commit. Mode is "Replace" (the default) or "AddUpdate" — see "Two
    import modes". The Confirmed inputs are the numbers the user confirmed;
    AddUpdate ignores them.
  → RowsRead, RowsCreated, RowsUpdated, RowsDeleted, RowsRejected (Integer)
    RowsDeleted is always 0 in AddUpdate mode
  → Rejections (ImportRejection List), ErrorMessage (Text)
  1.  Validate<Entity>Import(FileContent, FileName, Mode) — AGAIN. The preview
      proved the file against the table as it was; this proves it against the
      table as it is. ErrorMessage <> "" → return it, write nothing.
  2.  MODE GATE — the two modes diverge here, and only here.
        Replace + ANY rejection → write NOTHING, delete NOTHING. Return the
                                 counts and Rejections with RowsCreated /
                                 RowsUpdated / RowsDeleted all 0. A partial
                                 replace is the one outcome this mode must
                                 never produce.
        Replace + ToCreate, ToUpdate or ToDelete ≠ its Confirmed input →
                                 write NOTHING, delete NOTHING, all five
                                 counts 0, ErrorMessage "The <Entity> data changed after
                                 you confirmed, so nothing was imported. Press
                                 Import again to see the new numbers."
        Add and update          → proceed with ValidRows; the rejected ones are
                                 simply not written. Nothing is deleted.
  3.  UPDATE pass — ValidRows with a filled Id → Update<Entity>(full record).
      First, so a kept row stops referencing a row about to be deleted.
  4.  DELETE pass — Replace only: Delete<Entity> for each Id in DeleteOrder,
      in that order, counting RowsDeleted.
  5.  CREATE pass — ValidRows with a null Id → Create<Entity>. Last, so a new
      row never collides on a unique index with a row that is leaving.
      Per row, single-record actions throughout; NEVER CreateOrUpdate<Entity>
      — it INSERTS a row carrying a non-existent Id.
  6.  return the five counts + Rejections
```

Every numbered node above is a deliverable.

### Two Structures to define first

OutSystems has no anonymous record type, so both are real named Structures created before
any action references them:

- **`ImportRejection`** — `RowNumber` (Integer), `Reason` (Text). ONE structure for the
  whole app, shared by every entity's import action. Every `Rejections` output and the
  screen's rejection table are `ImportRejection List`.
- **`<Entity>ImportRow`** — the all-Text staging structure, one per entity. The parse reads
  it AND both downloads are generated from it, so the file the user gets and the file the
  parser expects are the same shape by construction. Described next.

### The staging structure — all Text, and it carries Id

`Excel To Record List` is strongly typed: it forces every cell into its declared type while
reading the file. So if `Record Definition` points at the entity, one bad cell — say text in
an Integer column — makes the parse throw before any row reaches your validation. The user
gets ODC's generic *"There was a problem. Please contact the administrator"* and loses the
whole sheet, good rows included.

So define `<Entity>ImportRow`, a Structure where **every attribute is Text — no exceptions,
including `Id`**:

- **One Text attribute per NON-`Id` entity attribute, plus a leading `Id` — every one Text,
  `Id` included.** The entity's own attribute list already contains `Id`, so "one per
  attribute, plus `Id`" would ask for a duplicate: take the non-`Id` attributes and add the
  leading `Id` yourself. If `Id` were a number type, a non-numeric value in that column would
  crash the whole parse — the exact failure this structure exists to prevent.
- **Copy each attribute's Name and Label from the matching entity attribute.** In OutSystems,
  Name is the internal identifier (no spaces) and Label is the display text (spaces allowed),
  so the two are not interchangeable. The Label is what becomes the column heading in both
  downloads.
- **A foreign-key attribute's Label must show a NUMBER is wanted — head it `<Referenced
  entity> Id`, never the bare entity name.** A column headed with just the entity name invites
  the user to type a name, which is then rejected as not a whole number.
- **Generate both downloads from THIS structure** — the blank template as an empty one, the
  current-data export filled with the real rows, and nothing else. That keeps the file the
  user downloads and the file the parser expects identical by construction.

**This all-Text rule is the single most important line in this section.** It is what makes a
bad cell a one-row rejection instead of a lost file. Text cannot fail to parse, so every row
survives to be validated individually.

### How the parse maps columns — the rule that decides everything

`Excel To Record List` has exactly five properties — `Name`, `Description`,
`Record Definition`, `File Content`, `Sheet Name`. **There is no header-row property and no
start-row property.** Row 1 is the header row and does not come back as a record.

But it is NOT true that the header text is ignored. Which matching method you get depends on
one thing, and the ODC documentation states it plainly:

> **By Position** — "If the number of columns and record attributes are identical, it maps
> sequentially, matching the first attribute to the first column, the second attribute to the
> second column, and so on."
>
> **By Column Name** — "If the number of columns and record attributes differ, it matches
> column headers to attribute labels (this matching is case-sensitive)."

**We deliberately sit in the positional branch.** A staging structure built
one-attribute-per-entity-attribute plus `Id` has exactly as many attributes as the download
has columns, so counts match and mapping is positional. That is correct here **because the
user is directed to start from a download every time**, so the column set and order are
already what the parser expects. Keep it that way and do not add machinery to change it.

The screen carries the only defence that matters here: tell the user to start from a
download and not to change its columns.

**Both downloads come from `Record List to Excel` over `<Entity>ImportRow`** — the same
structure the parse reads — so what the user gets and what the parser expects match by
construction. Generating either from the *entity* instead is how you ship a file that
imports zero rows.

- `GetTemplate<Entity>` → over an **EMPTY** list. Headers only, Id column blank.
- `ExportCurrent<Entity>` → over the entity's **real rows**, every attribute copied in as
  text and **`Id` filled from the record's Id**. This is the only way a user obtains Ids,
  so it is what makes the update path usable — it is a deliverable, not a nice-to-have.

Leave `Sheet Name` **blank** on the parse node so it reads the first sheet, and let
`Record List to Excel` write the template to that same first sheet.

**What that construction does NOT buy you.** It guarantees the template *starts* aligned. It
guarantees nothing once the user opens the file. Reordering its columns (while keeping the same
count) silently rewrites which field every later column feeds; adding or removing a column
changes the count and is matched by name instead. There is no separate check for this — the only
defence is the on-screen guidance above: the user must start from a download and not change its
columns.

### Converting Text safely — the built-ins throw, so wrap them

`TextToInteger`, `TextToDecimal`, `TextToDate`, `TextToDateTime`, `TextToTime` and
`TextToBoolean` can raise on bad input,
and a `ForEach` cannot catch a per-iteration exception. An exception handler is per-FLOW, so
one handler on a whole-row action would catch the FIRST bad cell and exit — the cells after it
would never be converted or diagnosed, and "list every fault on the row" would be impossible.
So the wrapping goes one level down, **per cell**:

- **One `Try<Type>` helper per converted type** — `TryInteger`, `TryDecimal`, `TryDate`,
  `TryDateTime`, `TryTime`, `TryBoolean`, `TryIdentifier` —
  `(Value Text, Label Text, IsMandatory Boolean) → (IsValid Boolean, Result <Type>,
  Reason Text)`. Each is its own server action with its own **All Exceptions handler** that
  sets `IsValid = False` and a `Reason` naming the label and quoting the value. A throw is
  caught there, and control returns to the caller for the next cell. They are shared across
  entities: one set per app.
- **`Convert<Entity>Row(StagedRow) → (IsValid Boolean, Record <Entity>, Reasons Text List)`**
  calls the matching helper for EVERY cell, appends each failing helper's `Reason` to
  `Reasons`, and sets `IsValid = Reasons is empty`. It never stops at the first failure. Text
  attributes need no helper — only the trim and the mandatory check below.

**But the handler is only a safety net, not your validity test.** A bad cell can be silently
coerced to the type's default instead of raising — so a row can come back `IsValid = True`
with nothing ever reaching the handler. Validate every value explicitly, and have the caller
branch on `IsValid` — never let an output's default value stand in for a real check. (Whether
a given bad cell coerces or raises varies by tenant; write the check so it is correct either
way.)

**Per cell: trim, then take exactly one of two branches — there is no third.**

- **Empty after trimming** → skip the conversion, leave the attribute at its default, and
  reject only if the entity attribute is mandatory. (Without this, a blank in an optional
  Integer or Date column would wrongly reject the whole row.)
- **Non-empty** → convert it, then confirm the result. A conversion that fails — including
  one that silently returns the type's default (`0`, `1900-01-01`, `False`) from a non-empty
  cell — is a **rejection**, naming the field by its label and quoting the offending value.
  (The only exception: the cell genuinely said "0", "1900-01-01", or "false".)

**`Date`, `Date Time` and `Time` are three different ODC types — cover all three.** Each has
its own converter (`TextToDate` / `TextToDateTime` / `TextToTime`) and its own default to
check against (`1900-01-01`, `1900-01-01 00:00:00`, `00:00:00`). Pin ONE canonical text form
per type — `yyyy-mm-dd`, `yyyy-mm-dd hh:mm:ss`, `hh:mm:ss` — validate against it, and have
**`ExportCurrent<Entity>` write the same form**, or the round trip fails on the app's own
export. Name the expected form in the rejection reason, the way the other types do.

**Booleans:** match against an explicit accepted set (`true`/`false`, `yes`/`no`, `1`/`0`,
case-insensitive) rather than trusting `TextToBoolean`. Do NOT put this set on the screen — the
three help lines at the top of §18 are the only on-screen guidance; instead name the accepted
values in the row's rejection reason when a value is not one of them.

**Dates:** accept ISO `yyyy-mm-dd` (what your own template produces) and reject anything else,
quoting the value in the reason. Reject ambiguous formats like `03/04/2021` rather than
guessing — reading it as the wrong month is worse than refusing it. Do NOT put the format on the
screen; instead name the accepted format (`yyyy-mm-dd`) in the rejection reason.

**"Mandatory" = the entity attribute's `Is Mandatory` property** — read it from the tenant
(`context_entities`); do not infer it from the attribute's name.

**Then validate the row as a whole:** mandatory attributes non-empty after trimming (a cell
of only spaces is empty), and every foreign key pointing at a row that actually exists (see
"Foreign keys"). That existence check is the difference between one rejected row and a whole
rolled-back run.

### Identity — the Id column, and NOTHING else

**Rows are matched on `Id` only. Never on a business key, never on a name, never on any
other field.** These are the only branches per row:

- **`Id` empty** → CREATE a new record. Count it as created.
- **`Id` filled AND a record with that Id exists** → UPDATE that record. Count it as updated.
- **`Id` filled AND no record with that Id exists** → **REJECT the row.** Do not create
  anything. Reason: `"No record with Id <value> exists"`. This is a hard rule: a user who
  typed an Id meant a specific record, and silently inserting a new one instead is the worst
  possible outcome — it looks like it worked and quietly forks their data.
- **`Id` filled but not a whole number** (`abc`, `1.5`) → REJECT, `"Id must be a whole
  number — got '<value>'"`.
- **`Id` filled AND an earlier row of the same file already used it** → REJECT this row,
  `"Id <n> appears more than once in this file — first on row <r>"`. Both rows pass the
  existence lookup, so without this check both update the same record and the last one
  silently wins: the updated count is wrong, and in Replace the table no longer holds one
  record per uploaded row. Track every filled Id in `SeenIds` during the validate-all pass,
  keep the first occurrence and reject every later one — before anything is written, in both
  modes.

So **look the Id up before writing**: an aggregate over `<Entity>` filtered on
`Id = <the converted Id>`, Max. Records 1. Found → update. Not found → reject. Never fall
through to a create.

**"The converted Id" means the Identifier idiom, exactly as for a foreign key.** The row's
own `Id` is an Entity Identifier too, so it is
`LongIntegerToIdentifier(TextToLongInteger(<staged Id text>))` — never `TextToInteger`,
which is the wrong width for a Long Integer key and yields an Integer rather than an
Identifier, truncating valid 64-bit Ids.

**Do not use the entity's `CreateOrUpdate` for the filled-Id case.** It decides create-vs-update
from the Id and will happily INSERT a row carrying a non-existent Id, which is exactly the
behaviour this rule forbids. Use the explicit lookup, then `Update<Entity>` on the found
record or `Create<Entity>` for the blank-Id case.

### Two import modes, and Replace is the point of the screen

The screen offers a **mode** control next to the Import button. It is a real, visible
choice — never a hidden default, because one of the two deletes data.

- **Replace all data for this entity (the default).** The uploaded file becomes that
  entity's contents: rows in the app that are not in the file are deleted. This is the mode
  the screen exists for — the user takes **Download current data**, which carries the app's
  existing rows as the worked example, edits it into their real data, uploads, and the sample
  data is gone. (**Download template** is the blank, headers-only sheet; it never carries
  rows.) Without Replace they would have to clear the seeded rows by hand, which defeats the
  point.
- **Add and update.** The incremental mode described in the Id rules below: blank Id
  creates, filled Id updates the matching row, nothing is deleted.

**Replace validates the entire file before it writes or deletes anything.** Run the full
per-row validation over the whole file first. If a single row is rejected, delete nothing,
write nothing, and report the rejections exactly as in Add-and-update mode. This is the whole
safety property of the mode: a Replace that drops the old rows and then fails part-way is
data loss with no undo, and the user has no copy of what was there. Make it impossible by
ordering the work, not by being careful. Add-and-update has the opposite behaviour by design
— good rows land, bad rows are reported.

**What Replace does NOT give you is per-row transactionality.** ODC runs one transaction
per server request, so an uncaught database error can still roll back writes already made
in the same request. Validating up front is what makes Replace safe, not per-row commits.

**Replace is two server calls: a preview that writes nothing, then the commit.** The user
confirms a Replace against exact numbers — how many existing rows will be deleted, created
and updated — and every one of those depends on parsing the workbook and comparing its
filled Ids with the rows in the table. The client cannot know them, so the confirmation
cannot come before a server call. So:

1. **`Preview<Entity>Import`** runs `Validate<Entity>Import` — every check the commit will
   run: empty / extension / size, the parse, per-row conversion and foreign keys, duplicate
   Ids, the orphan check and the delete-order cycle check — and returns the counts. It writes
   and deletes nothing. A refusal or any rejection is shown straight away and there is
   nothing to confirm.
2. **The confirmation shows the preview's exact `ToDelete` / `ToCreate` / `ToUpdate`** and
   names the entity. Never an estimate, never the table's current row count standing in for
   the deletion count. A user who uploaded a partial sheet by mistake is the case this
   catches: "40 will be deleted, 3 created" is the moment they notice. When nothing in the
   file matches an existing row (no updates) and rows would be deleted, the confirmation says
   outright that every existing row goes — that is the blank template filled with new rows and
   uploaded in Replace, the easiest way to empty a table by accident. A file with no data rows
   at all never gets this far: the empty-sheet refusal stops it in both modes, so an empty
   Replace is refused, never run.
3. **`Import<Entity>FromExcel` re-runs the same validation**, because the preview proved the
   file against the table as it was, not as it is now — another user may have added or
   removed rows in between. If its counts differ from the confirmed ones, it writes nothing,
   deletes nothing, and returns `"The <Entity> data changed after you confirmed, so nothing
   was imported. Press Import again to see the new numbers."` The user confirms again against
   the new numbers; a Replace never runs against numbers nobody saw.

Validation lives in ONE server action that both calls share, so the preview and the commit
cannot disagree about a row. **Add and update skips the preview** and calls the commit
directly: it deletes nothing, so there is nothing destructive to confirm.

**Replace must refuse rather than cascade.** Deleting a parent row that a child still
references either fails at the database or orphans the child, so before anything is deleted,
check whether any surviving row references a row this replace would remove — **two cases,
not one**: a row in ANOTHER entity, and a row in THIS one through a **self-referencing**
foreign key, where a row the file keeps can still point at an existing row the file leaves
out (the case people forget, because both rows are in the entity being replaced). The rows
the file keeps are written with the file's values, so check the file's self-reference values,
not the ones currently in the table. If either case turns one up, refuse the whole import and
name the blocking entity and the row, e.g. `"Cannot replace Customer: Order 1042 still
references Customer 7, which is not in the uploaded file."` or `"Cannot replace Employee:
Employee 12 reports to Employee 3, which is not in the uploaded file."` Do not cascade-delete
on the user's behalf — deleting rows in an entity they did not upload is never something to
infer. The user replaces the child entity first, then the parent.

**Rows being deleted can reference each other — delete child-first, and refuse a cycle.**
The orphan check covers rows that survive; it says nothing about references among the rows
that are all leaving. With a protected self-reference, deleting a parent before its
to-be-deleted child fails at the database, and because the commit is one transaction that
failure rolls the whole replace back as ODC's generic error — on a file that passed every
check. So `Validate<Entity>Import` orders the deletions: repeatedly take the rows in the
delete set that no other remaining row in the set references, and delete in that order,
children before parents. A row that points at itself deletes on its own and does not block
anything. If rows remain and none can be taken, they reference each other in a loop, and no
one-row-at-a-time order exists. **Refuse** — never cascade, never null the references on the
user's behalf: `"Cannot replace Employee: Employee 3 and Employee 12 reference each other
through Manager Id, and both would be deleted. Repoint or clear one of those references with
Add and update, then replace again."` Name every row in the loop. Because this runs in the
validation, the preview reports it before anyone confirms.

**In Replace mode the `Id` column is optional.** The file defines the new contents, so
blank Ids are the normal case. A filled Id is still honoured — it preserves that row's Id
across the replace, which matters when other entities reference it — and the same
"Id must exist" rule applies: a filled Id that is not currently in the table is a rejection,
not a create at an arbitrary Id.

**Report the deletions.** The results block gains a **deleted** count alongside created,
updated and rejected. A replace that deleted 40 and created 3 should look alarming, because
it is.

### Unique indexes — the commit order decides what can collide

Any entity can carry a **unique index** — a code, an email, a junction's pair of foreign keys.
Read every one off the tenant with `context_entities`; do not guess from attribute names. An
index is a database constraint, so a row that breaks it behaves exactly like a bad foreign key:
left to reach the write it fails the constraint, escapes as ODC's generic *"There was a
problem"*, and **rolls back the whole commit**. So `Validate<Entity>Import` checks each index
itself, against the order the commit actually runs in (update, then delete, then create):

- **Inside the file, both modes.** A later row repeating a key an earlier row of the file
  already claimed is REJECTED, `"<Label> '<v>' is already used on row <r> of this file"`. The
  database lookup cannot see this — neither row is in the table yet — and the second one would
  hit the index during the write.
- **Blank Id (create), which runs last.** In Add-and-update nothing is deleted, so an existing
  row holding the key is a real clash: REJECT, `"<Label> '<v>' already exists (Id <m>)"`. In
  Replace, check the file only: by the time creates run, the rows left are the ones the file
  keeps, carrying the file's values, and a row that holds the key today but is not in the file
  has been deleted — rejecting against it would refuse a legitimate file.
- **Filled Id (update), which runs before the delete pass.** Look the key up with **`AND Id <>
  <this row's Id>`** so the row does not match itself. If a DIFFERENT existing row holds it
  today, the update would collide mid-commit — in Replace that holder may be a row the file
  leaves out (still there, because deletes run after updates) or a kept row the file moves to
  another value (updates land in no guaranteed order). The final state may be valid; the
  sequence is not. REJECT, `"<Label> '<v>' still belongs to Id <m> when this row is updated —
  change it in a separate import once Id <m> no longer holds it"`. In Replace that rejection
  means nothing is written, so the user runs the replace without that one change (Id <m> goes,
  or moves off the value), then makes the change in a second import.

Refusing is deliberate. The alternatives — deleting before updating, or parking values on
temporary placeholders — trade this one visible refusal for either broken self-references or a
half-written table if anything fails part-way. A clear reason naming both rows is cheaper.

### Identity in Add-and-update mode

**Blank Id creates, every time, by design.** Re-uploading the same blank-Id file therefore
adds rows again. That is intended and agreed: the update path is the Id, and the way a user
gets Ids is the **Download current data** button. Say exactly that on the screen, and never
claim rows are matched on anything else.

### Foreign keys — matched on Id, ONLY on Id, and the parent must exist

An ODC foreign key is an attribute whose data type is `<Entity> Identifier`. There is no
separate "relationship" object — it is just another attribute, so it lands in
`<Entity>ImportRow` as **Text** like everything else and the parse cannot choke on it. That
part is free.

**A foreign-key column carries the referenced record's Id NUMBER — never a name, a code, or
any other display value, and the import must NEVER look a parent up by one.** (A hard rule;
builds have broken it twice.) Names are friendlier to type, but two parents can share a name
and then nothing can tell which was meant — the same ambiguity that Id-only *row* identity
exists to remove. Rows are matched on Id, so references are matched on Id.

Three things must agree, and getting any one wrong makes the feature unusable:

1. **The column heading ends in `Id`** — `<Referenced entity> Id`, never the bare entity
   name. A bare-name column invites the user to type a name, and the heading is the only clue
   they get.
2. **`ExportCurrent<Entity>` writes the Id number** in that column, not a looked-up display
   value.
3. **The import resolves it as an Id** — convert the text to a number and look the parent up
   by `Id` (per-row rules below).

**A valid number does not prove the parent exists.** A foreign-key value can convert cleanly
and pass validation — it is a whole number — and still reference no record, so the write would
fail on the database's referential integrity. Check existence *yourself, before writing* —
never let a bad reference reach the database. (The write is deliberately not wrapped in an
exception handler — one there would also swallow parse failures and misreport them — so a
referential-integrity failure escapes as ODC's generic *"There was a problem. Please contact
the administrator"*, and because the action runs in a transaction it **rolls back the whole
run**: every good row lost because one row pointed at a missing parent.)

So, per row, for **every** foreign key on the entity:

- **blank and optional** → leave it unset, carry on.
- **blank and mandatory** → REJECT, `"<Label> is required"`.
- **not a whole number** → REJECT, `"<Label> must be a whole number — got '<value>'"`.
- **a whole number, but no such row** → **REJECT**, `"<Label> <n> does not exist"`. Look it
  up: an aggregate over the referenced entity filtered `Id = <converted value>`, Max. Records
  1. Not found → reject that row and continue with the rest of the file.

One lookup per foreign key, per row — the same shape as the Id identity check above; it is
already in the action, so it is the cheapest thing to build correctly, and on a human-typed
file correctness matters far more than the query count. (If a file is ever large enough for
that to hurt, load the referenced entity's Ids once and check membership in memory — only
then, and never at the cost of the check.)

**Where the user gets the number:** the referenced entity's own **Download current data**,
which lists each Id against its name. That export is therefore a deliverable for EVERY
importable entity, not only the one being imported — for any entity with a foreign key it is
also the lookup table for its parents.

### Many-to-many — the junction entity imports like any other

A many-to-many relationship in ODC is stored as a **junction entity**: a third entity whose only
job is to hold two foreign keys, one of type `<Entity-A> Identifier` and one of type
`<Entity-B> Identifier`, alongside its own `Id`. There is no special "link" or "relationship"
object — the junction is an ordinary entity, so **it gets the full feature set, exactly like any
other entity: Import, Download template, and Download current data all work on it.** That means all
the usual per-entity artifacts: its own all-Text `<Junction>ImportRow`, `Convert<Junction>Row`,
`Validate<Junction>Import`, `Preview<Junction>Import` and `Import<Junction>FromExcel` (the
**Import** button), `GetTemplate<Junction>` (the **Download
template** button) and `ExportCurrent<Junction>` (the **Download current data** button). It appears
in the entity Dropdown automatically — with all three buttons active — because it has an import
action. Do not skip it, and do not fold the relationship into a parent entity's import — the pair
lives in the junction, so the pair is imported there.

Its template is `Id | <Entity-A> Id | <Entity-B> Id` — two foreign-key columns, each headed
`<Referenced entity> Id`, each carrying the parent's Id NUMBER. **Every foreign-key rule above
applies unchanged**: both columns resolve by Id only, both get an existence lookup before the
write, and a row pointing at a missing parent is REJECTED with `"<Label> <n> does not exist"`,
never sent to the database.

**The one thing a junction adds is pair uniqueness.** A many-to-many usually must not hold the
same pair twice, and the model enforces that with a **unique index on the two foreign keys**. That
index is covered by the general rule in "Unique indexes — the commit order decides what can
collide", with the pair as the key and the reason worded for a link: `"<Entity-A> <a> is already
linked to <Entity-B> <b>"`. The update branch's `Id <>` exclusion matters most here: without it,
re-uploading the junction's own **Download current data** file rejects every existing link as
"already linked" instead of updating it — breaking the round trip.

(If the junction has **no** unique index on the two keys, a
repeated pair is a legitimate duplicate row and this check does not apply — read the index off the
tenant with `context_entities`, do not assume one way or the other.)

Everything else — ordering (import both parents first, which the FK rejections already teach), the
Id identity branches, per-row writes, and the counts-and-rejections reporting — is identical to any
other entity. A junction is not a special case on the screen; it is one more entry in the Dropdown.

### Both downloads must be re-uploadable — no joins in the export

`ExportCurrent<Entity>` reads the entity's **own attributes only**. Do not join to the parent
entities to fetch display names, and do not add, remove or reorder columns. It must emit the
**same columns in the same order as the template**, because its whole purpose is that a user
can download it, edit a value, and upload it straight back.

**Ordering teaches itself — the on-screen line is for something else.** A child file uploaded
before its parents rejects every row with `"<Label> <n> does not exist"`, which already tells
the user to import the parents first. Let that happen: do not pre-empt it with a wall of
instructions, and do not collapse those rejections into a file-level refusal (see "File-level
failures").

**What the rejection cannot catch — the only silent-corruption path left — is a guessed Id.**
A user cannot fill a foreign-key column before the parent rows exist, because the platform
assigns Ids on create; so someone preparing a child sheet in advance is tempted to guess the
parents' Ids in the order they listed them. If the real Ids differ — a different insert order,
or existing rows shifting where numbering starts — every foreign key is a valid number pointing
at the WRONG parent. The existence check passes, the write succeeds, and the rows attach to the
wrong parents, with nothing downstream able to detect it.

**So the line next to the entity picker is not "import in this order" — it is "get the numbers
from Download current `<parent>`, do not type them from memory."** State it next to the picker,
not buried in a help paragraph.

**Convert a foreign key with the Identifier idiom, not `TextToInteger`.** An entity identifier
is a **Long Integer**, so the conversion is `LongIntegerToIdentifier(TextToLongInteger(<staged
text>))`. `TextToInteger` is wrong twice: the wrong width for a Long Integer key, and an Integer
is not an Identifier. (§11 uses the same idiom for dropdown pickers.)

**The UPDATE branch must write the FULL record, or foreign-key changes silently do not
persist** — the worst trap here, because it reports success. If the update writes only the
scalar columns (omitting the FKs), a user who repoints a row and re-uploads is told the row
updated while every foreign key stays exactly as it was, and nothing in the counts, the
rejections, or the screen reveals it. So the update branch calls the entity's own
**`Update<Entity>(Rec)` with the whole record, FKs included**. Verify it properly: change one
row's FK, re-upload, then **re-download current data and confirm the new value came back** —
not by glancing at a list screen, which may show a different attribute.

**Same-file and self-referencing foreign keys cannot be resolved.** A row cannot point at
another row created by a later or earlier line of the same upload, because its Id does not exist
until the platform assigns it. A self-referencing foreign key therefore only resolves against
rows that ALREADY exist. Do not attempt to resolve within-file references, and do NOT add a
self-reference note to the screen — the three help lines are the only on-screen guidance; a
self-reference to a row that does not yet exist is already rejected by the FK existence check
above (`"<Label> <n> does not exist"`), which tells the user what happened.

### Write per row, not in bulk

The entity's **bulk** `CreateOrUpdate` takes a whole `Source List` in one call and is
faster — and it is the wrong choice here. Swallowing the list in one call makes per-row
validation, per-row identity lookup and per-row rejection reasons impossible, and this
screen needs all three. **Use the single-record action inside the loop**, and accept the
extra round trips: correctness per row beats speed on a file a human just typed.

**What per-row buys you, and what it does not.** It buys per-row **validation**: a row
rejected by conversion or by a foreign-key check never reaches the database, so the rest of
the file still imports. It does **not** buy per-row **transactionality**. ODC runs one
transaction for the whole server request, so an uncaught database error on row 400 — a
constraint violation, a race — rolls back the 399 writes before it. Say that plainly rather
than promising an isolation the flow does not have. If rows genuinely must survive
independently, the write has to cross a real transaction boundary — a **Service Action** per
row — and its failure has to come back as a rejection reason like any other.

**Look the action names up on the tenant** (`context_actions`) rather than assuming: the
single-record and bulk variants differ in both name and input (`Source` vs `Source List`),
and a guess produces a compile error or a silent no-op.

### ONE screen with an entity Dropdown — and how to build it so it lands

`Excel To Record List` binds to a structure fixed at design time, so there is no generic
importer: each entity still needs its own `<Entity>ImportRow`, `Convert<Entity>Row`,
`ParseImportSheet<Entity>`, `Validate<Entity>Import`, `Preview<Entity>Import`,
`Import<Entity>FromExcel`, `GetTemplate<Entity>` **and
`ExportCurrent<Entity>`** — the current-data download is per entity like the rest, and it is
the only way a user gets the Ids the update path matches on. But there is **ONE screen**,
`ImportData`, reached from a **single top-menu entry**, and the user picks the entity from
a **Dropdown** on it. Do not build one screen per entity, and do not put an Import button
on the entity list screens — the top menu is the only route in.

**The entity picker is a `Dropdown` widget that renders as an HTML `<select>`. Nothing may be
substituted for it.** This is a hard gate, not a preference.

**Explicitly forbidden:** a row of buttons or pills, a tab / sub-tab strip, a segmented or toggle
control, radio buttons, a list of links, cards, or any hand-rolled selector. Any of these **is a
`failed` build, not an acceptable variant** — even if it works, even if it looks cleaner. The only
correct widget is the reactive `Dropdown` (`<select>`).

If the Dropdown will not bind, the plan item is **`failed`, with the binding error as the
reason** — never `done` with a substitute in place, and never a silent swap. A build that
ships buttons (or any form above) has not built this screen; report it as incomplete and hand back
the error, so the next turn fixes the binding instead of inheriting the workaround.

**It is also the single most expensive widget here, so build it exactly as specified and do
not explore.** Do not let Mentor discover the options binding — specify it:

- **A plain native `Dropdown`** that renders as a `<select>` — no OSUI variant, no icons, no size
  enums, and never a button/pill/tab substitute.
- Give it an associated **visible `Label` — "Entity"** — wired as the Dropdown's label so it
  becomes the field's accessible name. A screen reader must be able to announce what the combobox
  is; the selected option (`"Select an entity…"`) is its *value*, not its name. Never leave the
  Dropdown unlabelled.
- Its variable is a **Text screen local `SelectedEntity`**, default `""`.
- Its options are a **screen-local `EntityOptions` list of a NAMED record type** — reuse
  `OutSystemsUI.DropdownOption` (`Value` Text, `Text` Text) or a local Structure with the same two
  Text fields, mapped to the Dropdown's Value/Text; OutSystems has no anonymous records, so the
  list must have a declared type. Populate it with literal `Append` steps in the screen's
  `OnReady`: **first append the placeholder row** (`Value = ""`, label `"Select an entity…"`),
  **then one `Append` per entity** that has an import action, each with `Value` and label set to the
  entity's name. That is ONE mechanism, not a choice: do not bind the Dropdown to an aggregate, a
  Static Entity, or any other list source. A short known-at-build-time list needs no data source.
- The placeholder is that **first `Value=""` / `"Select an entity…"` row in the list** (appended
  above) — **not** the Dropdown's `Prompt` property, which can render blank or a raw value
  (§5). `SelectedEntity` starts `""`, so that row is the unset state.
- `OnChange`: set `SelectedEntity`, and **clear the previous run's counts and rejection
  table**. Stale counts from a different entity are actively misleading.

**Progressive disclosure — nothing but the Dropdown shows until an entity is picked.** The
template button, **the `Download current data` button**, the upload control, **the
Replace / Add-and-update mode control**, the Import button and the results block all have
`Visible = SelectedEntity <> ""`. Otherwise a user uploads before choosing a target and
gets an error for no reason — and a download button with no entity picked has no action to
dispatch to at all.

**Routing.** All four client actions — `Import`, `CommitReplace`, `Download template` and
`Download current data` — `Switch` on `SelectedEntity` and call that entity's typed server
action: `Import` calls `Preview<Entity>Import` in Replace mode and `Import<Entity>FromExcel`
in Add-and-update mode, `CommitReplace` calls `Import<Entity>FromExcel`, and the downloads call
`GetTemplate<Entity>` and `ExportCurrent<Entity>`. One screen, N typed actions behind a Switch.
Wiring only the template leaves the update path dead: without the current-data export the user
never obtains the Ids that rows are matched on.

### Keep the widgets boring, and split the turns

Plain `Button`, `Upload`, `Table`, and a plain `Popup` for the Replace confirmation — no
icons, no OSUI size/variant enums. This is a utility form, not a place for styling.

Build one entity's server actions per Mentor turn, and land upload → import (validate, preview,
confirmation, commit) → results before
the template/export actions (each in its own later turn) — all within outsystems-app-build §0's
~5-changes-per-turn ceiling.

### Reaching it — the top menu, and nothing else

The single top-menu entry to the `ImportData` screen is the only route in (see the plan
items). Three ODC-specific constraints beyond that:

- It must be a **real screen** reached from the menu — **not a modal** (a modal has nowhere
  for the rejection table; it may be an addition, never a replacement) and **not the
  create/edit form**.
- If the menu entry's visibility is role-conditional, do **not** use `Check<Role>Role()` —
  that built-in is removed and causes a deterministic deploy failure (`OS-BLD-40409`).
- **Use the app's standard layout — ONE header, and never add your own.** `ImportData` sits in
  the same Layout/template as every other screen, which already renders the top menu. Do NOT
  drop a `Header`, `Menu`, or any navigation block onto the `ImportData` screen itself. A second
  header block renders the entire top bar **twice** — two logos and two menus stacked — which is
  the visible tell that the screen is carrying its own copy on top of the layout's. If the menu
  is duplicated in preview, the screen has an extra header block: remove it, don't restyle it.

### Access — this ONE screen is gated, nothing else changes

Gate `ImportData` with **`AnonymousAccess = False`** plus the app role — in ODC that property
is what gates a screen, **not the `Roles` list alone** (role-only reads gated in the model but
ships wide open in the browser). Change nothing else. If the app's auth is wired-but-not-activated
the screen is then unreachable by anyone — gate it anyway and tell the user plainly, with the
steps, that auth must be activated and the role granted before it works.

### Build it open, gate it last

Build and drive the whole screen while it is still **Anonymous** (once gated, nobody —
including you — can open it); set `AnonymousAccess = False` and add the role as the **last edit
before publish**, then confirm a signed-out request bounces to Login while other screens still
load.

### File-level failures are messages, never an error page

**The Upload widget's `accept` attribute is NOT a check** — it is only a picker display hint.
It is bypassed by "All Files", drag-and-drop, automation, and any direct call to the server
action, and even when applied it matches the filename suffix, not the content. Keep it as a
convenience; never count it as the check. (This rule is easy to drop, so it is a plan item —
`Import file checks and on-screen guidance` in the agent/planner prompts; mark it `failed` if
any part is missing.)

**Why the check runs in both layers (per the table), and once:** the client one is the only
layer that can stop an over-cap request being *made*; the server one is the backstop when the
client is bypassed (a direct call, or a later regression). Use the identical expression in
both so they cannot drift.

**A message that is computed and not displayed is a missing message.** Bind the error text
into the page (not a transient toast), show it whenever `ErrorMessage <> ""`, and verify by
uploading a `.csv` and *seeing* the sentence on screen — "the string exists in the model" is
not proof.

**Name check vs. parse wrapper — build both, and don't let either cover the other's case.**
The extension check stops the honest mistake (a `.csv` picked by accident), early and with a
friendly message; it is *not* a defence against a caller sending arbitrary bytes under a valid
name. What actually gates bad bytes is the parse wrapper (below).

**Writing the check.** OutSystems has **no `EndsWith` and no `Contains`** — using them is a
compile error, so build it by hand, as a whitelist. **Take the text AFTER the last dot and
compare it to the BARE tokens `xls` / `xlsx` / `xlsb` — no leading dot on either side.** Find the
last dot with `Index` using its search-from-end option, `Substr` from just past it to the end of
the name, lower-case that, and accept only if it exactly equals `xls`, `xlsx` or `xlsb`. **Do NOT
grab a fixed number of trailing characters and compare them to a dotted literal.**
`Substr(FileName, Length(FileName)-4, 4) = ".xlsx"` is a real bug that ships a screen where
**every file is rejected**: the last 4 characters are `xlsx`, which never equals `.xlsx` (that
string is 5 characters, counting the dot), so the branch can never be true — and the same
off-by-one sinks `.xlsb` and `.xls`. The rule: if the dot is on one side of the `=`, it must be on
both, and the character count must match. Intended edge behaviour: a name with no dot is refused;
`book.xlsx.csv` yields `csv` and is refused; `.XLSX` is accepted (lower-cased first); `.xlsm` is
deliberately out — do not silently widen the whitelist.

| Case | Detect | Message |
|---|---|---|
| Wrong file type | the text **after** the last dot of `FileName`, lower-cased, not in the **bare** tokens `xls`/`xlsx`/`xlsb` (no dot on either side) — checked in the client action AND again in the server action | "Only .xls, .xlsx and .xlsb files are supported — save your file as .xlsx and try again." |
| Empty or missing file | `UploadedFile` is null or zero length | "That file appears to be empty — check the file and try again." |
| Over-size | Measure the binary against a pinned constant — **10 MB = `10485760` bytes**, the number written next to the message so the boundary cannot drift from the words. Check it in **BOTH** layers, like the extension check: in the CLIENT action **before** calling the server (so an over-cap request is never even sent), **and again in the server action** as the backstop — because the client is not a trust boundary and, when the tenant request limit is higher than the cap, a direct caller can otherwise slip a file between the cap and that limit straight through. There is **ONE effective cap and one number for it**: default it to 10 MB and confirm the tenant's request limit is at least that — if the tenant's limit is lower, that becomes the cap, and the constant, both checks, the on-screen help line and the message all carry the same new number. Never state one number and enforce another. If the size cannot be measured in a client action on this tenant, keep the server-side check **and** say on screen that files near the cap may be refused by the platform with a generic error — never promise a friendly message for a case you cannot detect. | "That file is larger than the 10 MB limit — split it and import in parts." |
| Empty sheet | `StagedRows` is empty | "No data rows found. The first row must be the column names; data starts on row 2." |
| Unparseable sheet | `ParseImportSheet<Entity>` returned `IsReadable = False` | "Couldn't read that sheet — it may be corrupted or not a real Excel file. Download the template from this page and try again." |

**Wrapping the parse is not a per-node operation.** OutSystems exception handlers are
per-**FLOW**, so an All Exceptions handler on `Import<Entity>FromExcel` would also catch the
**writes** — a failed write would then be reported as *"Couldn't read that sheet,"* turning a
data-loss bug into an invisible one. So the parse gets its **own** server action,
`ParseImportSheet<Entity>(FileContent) → (StagedRows, IsReadable)`, with its own All Exceptions
handler returning `IsReadable = False` (same pattern as the `Try<Type>` cell helpers, one node
earlier). Log the real exception even while showing the friendly text, or a transient platform
fault masquerades as a bad file and sends the user to re-save a good one.

**Do NOT build a byte-signature / magic-number check.** A valid header (a ZIP header for
`.xlsx`/`.xlsb`, an OLE2 header for `.xls`) is also present on a `.docx`, a `.jar` or a renamed
`.zip`, each of which still throws in the parse — so the wrapper is needed regardless and the
sniffer only re-covers a subset of it, at the cost of a byte-reading construct used nowhere
else. The extension whitelist in both layers plus the wrapper is the whole defence.

**The refusal path.** Any file-level refusal must set `HasRun = False`, clear the counts
(`RowsRead / RowsCreated / RowsUpdated / RowsDeleted / RowsRejected`), `Rejections` and the
Pending counts, close the confirmation, show the message, and
**END** the client action — never fall through to the server call after a message, and never
leave a previous run's counts on screen underneath a refusal. The same holds for a refusal the
server returns — from the preview (an orphan, a delete cycle) or from the commit (the data
changed after the user confirmed).

**Many rows failing on the same column is EXPECTED — do NOT collapse the per-row rejections
into a file-level refusal.** The common cause is ordering: a child file uploaded before its
parents has every foreign key pointing at nothing, so every row rejects on that column with
`"<Label> <n> does not exist"`, which tells the user to import the parents first. A single
"your columns are wrong" refusal would be a false diagnosis, sending them to fix a file that
was never the problem.

Show every rejection. If the table is capped for very large files, say how many were not
listed — never silently truncate, or the counts and the table disagree.

### Reporting the outcome

Show all five counts — read, created, updated, **deleted**, rejected — plus a table of
rejected rows, and a `Content\BlankSlate` before the first run. These are what the commit did;
the preview's to-create / to-update / to-delete numbers belong in the confirmation only, never
in the results block. A silent "success" toast is how a zero-row
import passes review.

**Reasons must name the field that failed and quote the value**, and list every fault on the
row, not just the first. A real run rejected four rows and told all four "Title and Author
are required" when only one was missing both — the user fixing row 3 hunts for a title that
is already there. Write:

- `Row 2: Title is required`
- `Row 5: Title is required; Author is required`
- `Row 4: Pages must be a whole number — got "not-a-number"`
- `Row 5: Published On is not a valid date — got "31/02/2021"`

Name the field by its **label** — what the user sees in their sheet.

### Verifying — you cannot upload, and "cannot upload" is NOT the end of the section

**You genuinely cannot drive the upload.** The preview tools have no upload primitive and no
JavaScript execution, so the spreadsheet→rows round trip is out of reach.

**But do not stop at structural checks.** "Screen renders, Upload widget present, server action
exists, no validation errors, entity reachable" — a build with ZERO row validation passes all
five. So verification is two parts:

**1 — Check statically what does not need a file.** All of these are readable off the tenant
with `context_actions` / `context_screens`, and none may be skipped:

- the client action runs the file checks in the canonical order — **empty, then extension,
  then size** — and ENDS on the refusal branch (no fallthrough to the server call). An
  extension-first order reports "wrong file type" for an empty upload;
- **Replace is two server calls**: the `Import` client action calls `Preview<Entity>Import`
  first, and the confirmation shows the preview's `ToDelete` / `ToCreate` / `ToUpdate` and
  names the entity — a confirmation built from the table's current row count, or with no
  numbers, is the estimate this design exists to replace. Cancel sends nothing. Add-and-update
  calls `Import<Entity>FromExcel` directly, with no confirmation;
- **`Validate<Entity>Import` is the only validation** — `Preview<Entity>Import` and
  `Import<Entity>FromExcel` both call it and neither re-implements a check, and neither
  `Validate` nor `Preview` contains a Create, Update or Delete node;
- **`Import<Entity>FromExcel` re-validates and compares**: in Replace, counts that differ from
  its `Confirmed…` inputs return the changed-data message having written and deleted nothing;
- `Validate<Entity>Import` starts with the **mode check** — anything other than `Replace` or
  `AddUpdate` returns the unsupported-mode message before the parse — and repeats the
  extension test on its `FileName` input;
- **every unique index on the entity is checked in validation** — in-file repeats, creates
  against the table in Add-and-update, and updates against a DIFFERENT row holding the key
  today, in both modes;
- `ParseImportSheet<Entity>` exists as its OWN action and carries an All Exceptions handler;
- **every attribute of `<Entity>ImportRow` is Text, `Id` included** — one typed attribute
  here reintroduces the lost-file bug;
- every typed cell converts through its own `Try<Type>` helper with its own All Exceptions
  handler, and `Convert<Entity>Row` collects every helper's reason — one handler on the whole
  row reports only the first bad cell; every typed conversion has a failure branch that sets
  `IsValid = False`;
- the Id path has all three branches: blank → create, filled+found → update,
  **filled+not found → REJECT** (never a create);
- **a filled Id already used by an earlier row of the file is REJECTED**, naming that earlier
  row — trace `SeenIds` through the validate-all pass;
- **every foreign key on the entity has an existence lookup before the write**, and its
  not-found branch REJECTS the row rather than letting the write attempt it;
- **every FK column heading ends in `Id`** (`<Referenced entity> Id`, never the bare name);
- **`ExportCurrent<Entity>` has NO joins** — same columns, same order as the template, and
  every reference column holds a NUMBER, not a parent's name;
- **the FK lookup filters on `Id`** — a lookup filtering on `Name` or any other attribute is
  the forbidden name-resolution and must be rewritten;
- **the entity picker is a `Dropdown` that renders as a `<select>`** — read the running screen;
  if the entities appear as a row of buttons, pills, tabs, or any non-`<select>` control, the
  screen is **FAILED** and the picker must be rebuilt as a Dropdown (this is the single most
  common substitution — check it every time);
- **all THREE help lines are visible on the screen** (accepted types + cap; start-from-a-
  download-and-do-not-change-the-columns plus what each mode does and the Id behaviour in
  BOTH modes; reference-Id behaviour) — read
  them with your own eyes, do not grep the model;
- **the screen renders exactly ONE header/menu** — a doubled top bar means an extra
  `Header`/`Menu` block was added to the screen and must be removed (it should inherit the
  layout's, like every other screen);
- **a rejection's row number equals the SHEET row** (staged index + 2), checked against one
  real spreadsheet;
- FKs are converted with `LongIntegerToIdentifier(TextToLongInteger(...))`, not `TextToInteger`
  — **and so is the row's own `Id`**, which is an Entity Identifier for the same reason;
- **the mode control is visible on the screen** and defaults to Replace, `Import<Entity>FromExcel`
  takes the mode, and the results area shows a **deleted** count alongside read / created /
  updated / rejected — a Replace that reports no deletions is the tell that the mode never
  routed;
- **Replace writes nothing when any row is rejected** — trace the flow: the validate-all pass
  completes before the mode gate, and the gate's Replace branch returns without reaching the
  update, delete or create pass;
- **Replace refuses rather than cascades** when a surviving row references a row it would
  remove — another entity's row, or a self-reference in the file's values;
- **deletions follow `DeleteOrder`, child-first**, and a loop of references among the rows
  being deleted is REFUSED with every row in it named — never a cascade;
- **the commit runs update, then delete, then create**;
- **the update branch calls `Update<Entity>(Rec)` with the FULL record** — a partial update
  that omits the FKs reports "updated" and changes nothing (§11);
- `ExportCurrent<Entity>` exists and fills the Id column;
- the message strings are present in the model verbatim, AND the screen actually renders
  `ErrorMessage` — present in the model is not enough, the screen must show it;
- the size constant in the check equals the number in the on-screen help text.

**2 — Hand the round trip over as UNVERIFIED, with the files named.** Do not report the import
as tested because the screen rendered. Say explicitly that it needs a human with real
spreadsheets, and list them so the person does not have to invent the matrix:

| Probe | Must produce |
|---|---|
| Blank template filled with valid rows, Id left blank | all **created** |
| **Download current data**, change a value, upload it back | all **updated**, zero created — this is the round trip the Id path exists for |
| A row whose Id is filled with an Id that does NOT exist | that row **REJECTED**, `"No record with Id <n> exists"` — and **nothing created for it** |
| **A row whose foreign key names a parent that does NOT exist** | that row **REJECTED**, `"<Label> 999 does not exist"`, **the other rows still imported** — never the generic error page, never a rolled-back run |
| **A row whose FK column holds the parent's real Id number** | **IMPORTED**, attached to that parent. If a real Id is rejected as "not found", the build resolved by NAME — the forbidden design |
| **A row whose FK column holds the parent's NAME** | **REJECTED** as not a whole number. If a name imports, the build resolved by name |
| **On a junction with a unique index, upload a pair that already exists** | that row **REJECTED**, `"<A> is already linked to <B>"`, other rows still imported — never the generic error page, never a rolled-back run |
| **Download current data on a CHILD entity, then re-upload it unchanged** | all rows **updated**, zero created. If the columns come back joined/reordered the export has joins and cannot round-trip |
| **Read the screen** | all three help lines visible: what Replace deletes, the Id behaviour stated for both modes, reference-Id behaviour, accepted types + cap |
| **Any rejection** | its row number matches the row as numbered **in the spreadsheet**, not the data index |
| **Download current data, repoint one row's FK at a different parent, upload it back** | that row's FK **actually changed** — verify by re-downloading, NOT by looking at a list screen. "Updated: 1" with the old FK still in place is §11's silent partial-update bug |
| A row with a blank MANDATORY foreign key | rejected, `"<Label> is required"` |
| A row with a blank OPTIONAL foreign key | **created**, with no reference set |
| A child-entity file uploaded before any parent rows exist | every row rejected with a readable reason — never an error page |
| A row whose Id is `abc` | rejected, `"Id must be a whole number"` |
| A missing mandatory value, otherwise valid | that row rejected, field named, other rows still imported |
| A non-numeric Integer / unparseable Date / nonsense Boolean | that row **rejected** with the field named and value quoted, **other rows still imported** — never a whole-file failure, and never stored as `0` / `1900-01-01` / `False` |
| A genuine `.xlsx` renamed `.csv` | the wrong-file-type message, **visible on screen**, and the server never called |
| A `.txt`, a `.pdf`, and a name with no extension | the same message, visible |
| Garbage bytes named `.xlsx` | the unparseable-sheet message — **never** an error page |
| Header-only sheet | the empty-sheet message |
| **The blank template uploaded as-is in Replace mode** | the empty-sheet message; **nothing deleted** — an empty Replace is refused |
| **The blank template filled with new rows, uploaded in Replace over an entity with rows** | the confirmation opens with "Every existing <Entity> row will be removed" and states the exact count |
| **A direct call to `Import<Entity>FromExcel` with Mode `"Delete"`** | the unsupported-mode message, nothing written or deleted |
| **Replace mode, a kept row changes a unique value to one an omitted row still holds** (Id 1 → Code `B`, Id 2 holds `B` and is not in the file) | Id 1 **REJECTED**, naming Id 2; nothing written — never the generic error page |
| **One row with a bad Integer AND a bad Date** | ONE rejection naming BOTH fields — never just the first |
| **Replace mode: 3 rows uploaded over an entity holding 40** | the confirmation, BEFORE anything runs, says exactly 40 deleted / 3 created; after confirming, the results say 40 **deleted** / 3 created |
| **Replace mode, press Cancel on the confirmation** | nothing written, nothing deleted — re-download current data and compare |
| **Replace mode with ONE invalid row in the file** | the preview lists the rejection, **no confirmation is offered**, nothing deleted and nothing written |
| **Replace mode where a surviving row — in another entity, or in this one through a self-reference — points at a row the file leaves out** | the whole import **REFUSED** at the preview, naming the blocking entity and row; never a cascade delete |
| **Two rows in one file carrying the same existing Id** | the second **REJECTED**, `"Id <n> appears more than once in this file — first on row <r>"`. Replace writes nothing; Add-and-update updates from the first row only |
| **Replace mode omitting a chain of self-referencing rows** (12 reports to 3, both left out) | both **deleted**, no error — the child went first |
| **Replace mode omitting two rows that reference each other** (3 reports to 12, 12 reports to 3) | **REFUSED** at the preview, naming both rows; nothing deleted |
| **Replace mode, confirmation open, then add a row to that entity from another tab before confirming** | nothing written, the changed-data message on screen; pressing Import again shows the new numbers |

**Generate the probe files with a real spreadsheet writer** (e.g. `openpyxl`) or the app's own
downloaded template, and leave the output byte-for-byte alone — a hand-assembled or post-edited
xlsx can be rejected by the parse and read exactly like a product bug. If a probe file fails,
re-test it unmodified before concluding anything about the platform.

If a future harness gains an upload primitive or JavaScript execution, run the probes yourself
and delete this hand-off. Until then the hand-off IS the deliverable.

Export has the mirror trap: §15 requires checking the downloaded file off disk.
