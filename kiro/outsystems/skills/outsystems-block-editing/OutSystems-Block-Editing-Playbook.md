# OutSystems Block-Editing Playbook (Mentor / Model-API)
### Hard-won learnings from rebuilding a shared **navigation/header block**

This is a field guide for editing **shared UI blocks** (top nav / header / menu, footers,
reusable widgets) on an ODC tenant through the **Mentor flow** (`mentor_start` →
`applyModelApiCode`, which runs C# against the OutSystems Model API). The nav rebuild took
far longer than it should have; almost all the lost time came from a handful of specific,
avoidable traps documented below. Read this **before** starting a block edit.

---

## 0. TL;DR — the 10 rules that save the most time

1. The shared top nav is the **`Menu` block in the `Common` flow**. Screens are in `MainFlow`.
   The chrome wrapper is **`LayoutTopMenu` in the `Layouts` flow**.
2. **`IMobileWidget` has NO `.Name`.** Cast to a concrete `ServiceStudio.Plugin.NRWidgets.*`
   interface first (`IContainer`, `ILink`, `IExpression`, `IAdvancedHtml`). This one mistake
   caused ~10 min of identical compile-error looping, twice.
3. **No `for` loops, no `while` loops, no `System.IO`, no `System.Text.RegularExpressions`.**
   The sandbox rejects them (`DisallowedConstruct`). Use LINQ + `string.IndexOf/Substring/Replace`.
4. **Put all styling in the block's `StyleSheet` (CSS classes).** Don't fight per-widget inline
   styles. Editing one CSS rule = `IndexOf`/`Substring`/`Replace`, no loop.
5. **Never hide `.header`** or any element that *wraps* your custom bar — it nukes the whole header.
6. **Never set `Visible=False` on a container that also wraps the Menu block placeholder** — same effect.
7. **Never use `height:100%`** on the bar — the parent has no fixed height, it explodes to ~640px.
   Use the base header's fixed height: **`var(--header-size, 56px)`**.
8. **Keep data-URIs small (< ~1500 chars).** A 7,900-char base64 SVG made Mentor spin for ~8 min
   with zero output. Extract just the mark, minify, pair with HTML text for wordmarks.
9. **Small, focused runs (1–2 changes).** Big 4-in-1 runs get stuck on the hardest item and waste the rest.
10. **Verify at runtime after every change** (`browser_navigate` + `get_screenshot`). CSS only shows at
    runtime; `no_changes_detected:true` is normal (Mentor auto-saves) — never trust the revision number.

---

## 1. Where things live (the model map)

This is a Reactive web app, but the Model API exposes it through the **Mobile** namespace.

| Thing | How to get it |
|---|---|
| A flow | `eSpace.MobileFlows.Named("Common")` (also `MainFlow`, `Layouts`) |
| Blocks in a flow | `flow.Nodes.OfType<OutSystems.Model.UI.Mobile.IMobileBlock>()` |
| The shared nav | `Common` flow → `IMobileBlock` where `b.Name == "Menu"` |
| Screens | `MainFlow` → `IMobileScreen` (e.g. `Home`, `Login`, …) |
| The layout wrapper | `Layouts` flow → `IMobileBlock` `"LayoutTopMenu"` |
| Themes | `eSpace.GetAllDescendantsOfType<OutSystems.Model.UI.Mobile.IMobileTheme>()` — app theme is named after the app; base theme is `OutSystemsUI` |
| A block's CSS | `block.StyleSheet` (get/set **string**) |
| A block's inputs | `block.InputParameters` (e.g. the `ActiveItem` param) |

**Widget tree:** a block's direct children are `block.Widgets`. Each is an `IMobileWidget`.
Concrete widget interfaces live in **`ServiceStudio.Plugin.NRWidgets`**:
`IContainer`, `ILink`, `IExpression`, `IAdvancedHtml`, …

The `LayoutTopMenu` header structure (discovered):

```text
outerContainer → l1Container → [
  IAdvancedHtml   holds the <header>; its .Content.Widgets are
                  [ ILink "<App wordmark>" logo, IContainer hamburger-toggle, … ],
  IContainer      header row,
]
```

The **`Menu` block placeholder renders inside that structure**, so hiding an ancestor hides the nav.

---

## 2. The C# sandbox rules (what compiles and what doesn't)

### 2a. The `.Name` trap (biggest time sink)
- `IMobileWidget` — the base type you get from `.Widgets` / `.OfType<IMobileWidget>()` — **does not
  expose `.Name`.** `w.Name` → `CS1061: 'IMobileWidget' does not contain a definition for 'Name'`.
- ✅ **Get the widget name:** cast to a concrete interface that has it:
  ```csharp
  menuBlock.Widgets.OfType<ServiceStudio.Plugin.NRWidgets.IContainer>().First(c => c.Name == "Topbar")
  ```
  or pattern-match while iterating:
  ```csharp
  string name = w is ServiceStudio.Plugin.NRWidgets.IContainer c ? c.Name
              : w is ServiceStudio.Plugin.NRWidgets.ILink l ? l.Name : "?";
  ```
- ✅ **Get the widget TYPE name** (safe on the base type): `w.GetInterface().Name`
  (or `.GetInterface().FullName`). Use this to discover what a widget IS before casting.

### 2b. Disallowed constructs (hard failures)
| Construct | Error | Use instead |
|---|---|---|
| `for (...)` | `DisallowedConstruct: for loops are not allowed` | LINQ (`Select`, `First`, `Where`) |
| `while (...)` | `DisallowedConstruct: while loops are not allowed` | LINQ / recursion-free string ops |
| `new byte[N]` (sized array) | `DisallowedConstruct: Array creation with size specifiers is not allowed` | a `new byte[] { … }` initializer — and ONLY that form. `new byte[0]` is still a size specifier (same error), and `new[] { 137, … }` infers `int[]`, which the binary APIs reject |
| `Convert.FromBase64String(…)` / `Convert.ToBase64String(…)` / `Encoding.*` / any static call | `Static method calls are not allowed unless explicitly whitelisted` | carry the bytes as a literal `new byte[] { … }` (see section 6) — no `Convert`/`Encoding` |
| `using System.IO;` / `using System.IO.Compression;` | `Imports from disallowed namespaces: System.IO` | — (can't read/write files or deflate — so you can't *build* a PNG in-sandbox; embed pre-encoded bytes) |
| `using System.Text.RegularExpressions;` | disallowed | `string.IndexOf` + `Substring` + `Replace` |

**Allowed imports:** `System`, `System.Linq`, `OutSystems.Model`, `OutSystems.Model.UI.Mobile`,
`OutSystems.Model.UI.Mobile.Widgets`, `ServiceStudio.Plugin.NRWidgets`.

### 2c. Property-access gotchas
- `IContainer.Style` / `ILink.Style` return an **`IExpression`**, not a string. `cc.Style?.Value` →
  `IExpression has no 'Value'`. **Don't try to read inline styles.** Set them with
  `widget.SetStyle("\"my-css-class\"")` (the value string is quoted). For anything non-trivial,
  **edit the block `StyleSheet` instead of inline styles.**
- `ILink.OnClick.Destination` is an **`IObjectSignature`** — `.Name` fails on it. Set it, don't print it:
  `avatarLink.OnClick.Destination = loginScreen;`
- `IAdvancedHtml` has **`.Content.Widgets`** (a placeholder), not `.Widgets`, plus a `.Tag`.

### 2d. Reading values past truncation
`Console.WriteLine` output in the event stream is **truncated**. To reliably read a value during
investigation, throw it:
```csharp
throw new System.Exception("HEADER_SIZE=" + val + " | MAXW=" + maxw);
```
The exception message returns in full. (Purely a debug read; remove before the real edit.)

---

## 3. The reliable editing recipes

### 3a. Restyle → edit the block StyleSheet
```csharp
var mb = eSpace.MobileFlows.Named("Common")
    .Nodes.OfType<OutSystems.Model.UI.Mobile.IMobileBlock>().First(b => b.Name == "Menu");
string css = mb.StyleSheet ?? "";
// update ONE rule (single-brace) without loops:
int si = css.IndexOf(".app-topbar");
int bi = css.IndexOf('{', si);
int ei = css.IndexOf('}', bi);
string oldRule = css.Substring(si, ei - si + 1);
string newRule = ".app-topbar { display:flex; align-items:center; width:100%; height:var(--header-size,56px); ... }";
mb.StyleSheet = css.Replace(oldRule, newRule);
```
> Only works cleanly for rules with **no nested braces** (`@media`/keyframes need more care — but
> avoid those in a block stylesheet). Append brand-new rules by string-concatenation.

### 3b. Structural change → **replace the widget tree wholesale**
When you need to *restructure* (not just recolor), **clear the block's widgets and rebuild** rather
than introspecting/patching in place. This is how the initial nav succeeded and is the cleanest way
to strip unwanted chrome. Create widgets with `parent.CreateWidget<T>("Name")`, delete with
`widget.Delete()`, set classes with `SetVisible("True")`/`SetStyle("\"class\"")`, wire links with
`link.OnClick.Destination = screen`.

### 3c. Convert a Container to a navigating Link (e.g. avatar → Login)
```csharp
var avatar = topbar.Widgets.OfType<IContainer>().First(c => c.Name == "Avatar");
var textExpr = avatar.Widgets.OfType<IExpression>().First();
string val = /* keep its value */;
avatar.Delete();
var link = topbar.CreateWidget<ILink>("Avatar");
link.SetStyle("\"app-avatar\"");
link.OnClick.Destination = loginScreen;         // loginScreen from Common flow
foreach (var d in link.Widgets.ToList()) d.Delete();   // foreach is OK; for/while are NOT
var e = link.CreateWidget<IExpression>("AvatarText");
e.SetValue(val); e.SetStyle("\"app-avatar-text\""); e.Example = "AB";
```
> **Critical:** keep the verification `Console.WriteLine(... .Name)` OFF the same block — a single
> `.Name`-on-`IObjectSignature` compile error aborts the WHOLE script, so the edit above never runs.
> Verify in a *separate* follow-up call.

---

## 4. CSS / layout pitfalls that cost real time (whack-a-mole log)

- ❌ `.header { display:none !important }` → `.header` is the OutSystemsUI wrapper **containing** your
  bar. It hid the entire header (blank banner). **Never target `.header` or any ancestor.**
- ❌ `Visible=False` on the LayoutTopMenu **hamburger-toggle IContainer** → that container also wraps
  the Menu placeholder, so the whole nav vanished. Restore with `SetVisible("True")`.
- ❌ `height:100%` on the bar → parent has no fixed height ⇒ resolved to full viewport (~640px), content
  floated in the middle of a huge white box. ✅ Use **`height: var(--header-size, 56px)`** (fixed).
- ✅ **Base header height = `--header-size` (56px)** in OutSystemsUI. Match it exactly. A design's 64px
  overflows the 56px slot and the slot's (darker) background shows as a strip.
- ✅ **Align with content** by using the same spacing token the content uses: **`padding:0 var(--space-l,32px)`**.
  In this theme both header and content are **full-bleed (no max-width)** — matching the Figma. Don't invent
  a `max-width` the content doesn't have, or you'll *create* a mismatch.
- ✅ The OutSystemsUI responsive CSS **auto-hides the hamburger at desktop width**. Leaving the stock
  toggle `Visible=True` is harmless — don't spend a run trying to delete it.

---

## 5. Images / logos in a block

- **Embed as a base64 `data:image/svg+xml;base64,…` URI** in a CSS `background-image` on a sized div/class.
  Bulletproof (no external dependency) and verifiable in preview.
- **Keep it SMALL (< ~1500 chars).** A 7,934-char lockup data-URI made Mentor reason for ~8 min and never
  emit the apply. A 1,470-char mark-only data-URI applied first try. Extract only the paths you need
  (e.g. the logo *mark*, not the full mark+wordmark lockup), minify (`>\s+<`→`><`), and render the
  wordmark as plain HTML text next to it.
- **External hotlinks are risky:** Wikimedia blocks datacenter IPs (curl needs a UA; thumb rendering can
  429). If you must, verify it renders in the *preview browser*, not just curl.
- **Verify the asset visually** before wiring it: write a tiny local `.html` referencing the SVG, serve it
  (`setsid python3 -m http.server`), and `get_screenshot` it.

---

## 6. App icon & browser favicon — two DIFFERENT targets

Setting "the app's icon" is two distinct model objects, and the obvious one only
changes half of what users see. Both are set via `applyModelApiCode`, and both
hit the sandbox's binary rule (section 2b): **the only way to get image bytes in
is a literal `new byte[] { … }` array** — `new byte[N]`, `Convert.FromBase64String`,
`Encoding.*`, and `System.IO*` are all blocked, so you cannot decode base64 or
build/deflate a PNG in-sandbox.

- **`eSpace.Icon` = the application icon** shown in the ODC Portal / Studio to
  identify the app. It does **NOT** change the runtime browser-tab favicon.
- **The browser-tab favicon = a module Resource named `favicon.png`** (RuntimePath
  `/<Module>/favicon.png`, `DeployAction = CopyToApplicationDir`), which ships the
  default OutSystems logo. To change the tab icon you must replace **that
  resource's content** — setting `eSpace.Icon` alone leaves the favicon untouched
  (verified: two `eSpace.Icon` publishes left `favicon.png` byte-identical).

**Generate the PNG yourself; hand Mentor the exact byte literal.** Do NOT ask
Mentor to *draw/generate* the icon procedurally — with no `System.IO.Compression`
it tries to hand-roll PNG encoding and loops on the sandbox for 10–20 min
(observed: two runs cancelled). Instead build a small PNG locally and give Mentor
the literal decimal bytes. Keep it tiny so the literal is transcribable and the
turn is deterministic — a flat palette or flat-RGBA icon compresses to ~150–600
bytes (a ~400–2000-char `new byte[]{…}` literal); a gradient/large image balloons
the literal (same "keep embedded assets small" rule as section 5).

```csharp
// Replace the favicon.png resource content (delete + recreate keeps it clean):
var existing = eSpace.Resources.Named("favicon.png");
if (existing != null) existing.Delete();
var res = eSpace.CreateResource(new byte[] { 137,80,78,71, /* …full PNG bytes… */ }, "favicon.png");
res.DeployAction = OutSystems.Model.Enumerations.DeployAction.CopyToApplicationDir;
// (imports: OutSystems.Model, OutSystems.Model.Data, OutSystems.Model.Enumerations)
```
Set `eSpace.Icon = new byte[] { … };` too if you also want the Portal app icon to
match. Keep the resource **named `favicon.png`** — ODC appends a content-based
version token to its URL, so browser caches bust automatically when the bytes change.

**Verify at runtime — a clean publish does NOT prove the icon changed.** Both
`eSpace.Icon` publishes above succeeded (`change_applied:true`, revision bumped)
yet the favicon never moved; only a byte comparison caught it. Fetch
`<app-url>/moduleservices/moduleinfo`, read the current `favicon.png` version
token from `manifest.urlVersions`, GET `<app-url>/favicon.png?<token>`, and
SHA-256 / pixel-compare it to your source PNG. If the served bytes match your
source (and the token changed), it landed.

---

## 7. Process / orchestration learnings

- **One or two changes per `mentor_start`.** A 4-in-1 header run got stuck on item 4 (chrome removal) and
  the important items 1–3 (logo, login, active-pill) never landed. Order by priority so the must-haves go first.
- **Resume the same session** (`mentor_session_id` + refreshed `mentor_session_token`) for follow-ups —
  Mentor keeps the block-structure context and jumps straight to the right widgets instead of re-exploring.
- **A refreshed token only comes from a *terminal successful* run's `result`.** A cancelled run gives none —
  so you can't publish after a cancel unless you still hold a valid earlier session token.
- **Cancelling can roll back that run's applied edits.** Cancelling the 4-in-1 run lost the logo + avatar
  changes (they had to be redone). Only cancel a run that is *looping unproductively before any edit landed*;
  otherwise let it reach terminal.
- **Anti-loop guardrail — put this in every block-edit prompt:**
  > "Do NOT enumerate widgets by `.Name` (IMobileWidget has no `.Name`); cast to typed
  > `ServiceStudio.Plugin.NRWidgets` interfaces. No `for`/`while` loops, no `System.IO`/regex. If a probe
  > fails once, change approach — do not repeat the same failing call. Put styling in the block StyleSheet."
- **Publish reality:** `no_changes_detected:true` is normal (Mentor pre-saves the revision, AVS de-dups the
  upload). The revision number incrementing is **not** proof. **Always verify at runtime** with a fresh
  `browser_navigate` + `get_screenshot` (and check the a11y `banner`/DOM), because CSS/layout only manifests
  at runtime.
- **Preview width caveat:** the canvas browser is **floored at 1920px** (capped at 2400), so **narrow-screen
  misalignment can't be reproduced there.** Say so, and if the design implies a content max-width, match that
  exact value rather than guessing.

---

## 8. Ready-to-use Mentor prompt template (shared block restyle)

> **Edit the shared `<BlockName>` block in the `<Flow>` flow.** You know the model: this is a Reactive app
> exposed via the Mobile Model API; the block's children are `IMobileWidget` — **cast to
> `ServiceStudio.Plugin.NRWidgets` interfaces** (`IContainer`/`ILink`/`IExpression`/`IAdvancedHtml`) to read
> `.Name`/edit; use `w.GetInterface().Name` for the type. **No `for`/`while` loops, no `System.IO`, no regex.**
> Put ALL styling in the block's **StyleSheet** as CSS classes; to change one rule, `IndexOf`/`Substring`/`Replace`
> it (single-brace rules only). Do NOT hide `.header` or any element wrapping the bar; do NOT set `height:100%`
> (use `var(--header-size,56px)`); align horizontal padding to the content with `var(--space-l,32px)`. Keep any
> embedded image data-URI **under ~1500 chars**. Make exactly these **1–2 changes**: `<…>`. If any probe errors
> once, switch approach immediately — never repeat the same failing call. Validate and report 0 errors, and
> confirm each change is in the model **in a separate verification call** (so a print error can't abort the edit).

---

*Provenance: authored from a real navigation/header rebuild (the `Menu` block in
the `Common` flow). Every trap above was hit and resolved live during that work.*
