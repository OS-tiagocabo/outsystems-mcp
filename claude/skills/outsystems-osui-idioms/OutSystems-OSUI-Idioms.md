# OutSystems OSUI Idioms — block-mapping gate & day-0 checklist

> Canonical reference: the [OutSystems UI source and docs](https://github.com/OutSystems/outsystems-ui).

---

## Day 0 — before any screen

1. Invoke **outsystems-ui-exactness** (when a Figma design is in scope) or read
   `references/screen-guides/design-system.md`.
2. Set brand via **ThemeValues** (`PrimaryColor` / `SecondaryColor`) and `:root` OSUI variables:
   - `--color-primary` (+ `-hover` / `-selected`), `--color-secondary`,
     `--color-background-body`, `--header-color`, `--header-size`,
     `--border-radius-soft`, semantic success/warning/error.
3. Screenshot-verify **no default green** on buttons, radios, links, active states.
4. Replace template default layout with **LayoutTopMenu** when the design has an app header.
5. Brand auth screens (`Login`, `ChangePassword`, …) even when auth is wired-not-activated.

---

## Block-mapping gate

**OutSystems widgets before custom code.** Reach for a native widget or an OSUI
block first, every time, and use custom CSS only to style one. A screen built
from widgets stays inspectable and editable in ODC Studio (Widget Tree,
properties, the block's own toggles). A container that only behaves like a widget
because of custom CSS is opaque there: a CSS overlay (`position: fixed`, a
backdrop class, a high `z-index`) covers the canvas, so nobody can select or
change what is under it without first disabling the CSS. Custom CSS styles a
widget; it never builds one. If no widget fits, say so in the build report and
ask before hand-rolling one.

Every visual element → real OSUI block or documented utility. **FAIL** if you would
use `Container` + `Expression` + custom CSS where a block exists.

| UI element | Use | Never |
|------------|-----|-------|
| App header | `LayoutTopMenu` | Hand-built header container |
| Status chip | `Tag` / `Badge` | Container pill |
| KPI number | `Counter` | Raw `Expression` in a card |
| Search | `Search` / `SearchInput` | Custom search container |
| Text entry | `Input` / `Text Area` (native) | Styled `Container` posing as a field |
| Single-select | `Dropdown` (native); `DropdownSearch` (OSUI) for searchable / long lists | Hand-rolled repeater-in-popup dropdown |
| Boolean toggle | `Checkbox` (native) / OSUI `Switch` | Clickable container with state CSS |
| Date pick | OSUI `DatePicker` | Bare text `Input` + manual parsing |
| Breadcrumb | OSUI `Breadcrumb` | Hand-rolled markup |
| Primary action | `Button` (`btn btn-primary`, keep `btn` base) | Link styled as button |
| Navigation | `Link` (see `widget-link-slot` gotcha) | Button for navigation |
| Section layout | `Columns2`–`6`, `Gallery`, `MasterDetail` | `display-flex` / `display-grid` CSS |
| Modal / dialog / confirmation | native `Popup`, opened by a Boolean local bound to `ShowPopup` | `Container` + custom CSS backdrop (`position: fixed`, `z-index`) shown by toggling a class |
| Side panel / drawer | OSUI `Sidebar` | Fixed-position container slid in with CSS |
| Toast / transient notice | OSUI `Notification` | Absolutely positioned container on a timer |
| Tooltip | OSUI `Tooltip` | Hover container shown with CSS |
| Tabs | OSUI `Tabs` | Buttons swapping which container is visible |
| Expandable section | OSUI `Accordion` + `AccordionItem` | Clickable header toggling a container |

**Breadcrumbs:** non-current segments = clickable links (no underline); current page = plain emphasized text.

**Reserved class names** (`main-content`, `sidebar`, `header`, `content`, `footer`) — app-prefix them (`<app>-header`).

**No card-in-card:** inner `Form`/`Container` with default border inside a `Card` — clear border/background or place form on card directly.

**Source-name → block (non-negotiable):** when a Figma frame or layer is *named*
`Carousel` / `Carrousel` / `Slider`, `Gallery`, `Tabs`, `Wizard`, `Accordion`,
`Sidebar`, or `Stepper`, map it to THAT block — do NOT substitute `Columns3`
because the screenshot happens to show the items side by side. The source name is
the author's intent; look the block's args/placeholders up in
`references/outsystems-ui/ui-reference.md` + the matching
`references/outsystems-ui/patterns/*.md` before building it.

**The one legit `display-flex`:** `display-flex` on a widget's `Style` is allowed
ONLY for inline alignment INSIDE a single block placeholder — icon + text in a
`CardItem` slot, or "title left, action right" inside one `Card.Content`. It is
NEVER the tool for section- or screen-level layout where the children are
independent visual blocks; that is always `Columns2`–`6` / `Gallery` /
`MasterDetail`.

---

## Consuming a shared UI library — read the reference apps FIRST

Before you wire an app into a shared UI library / design system / suite theme,
spend **2–3 read-only calls** on the apps that already consume it. "Consume the
shared UI library" almost never means what you'd guess from the library's
contents.

- `app_refs` on a sibling consumer — what it *actually* depends on.
- `context_themes` on it — whether its theme **inherits (base-theme)** the shared
  theme.
- `context_search` / `context_screens` on one consumer's layouts — which chrome
  it actually renders.

**A shared library can ship a block that no consumer in the suite uses.** The
field case: a suite's shared UI library exposed an app-shell layout block,
so "adopt the shared UI" looked like re-chroming every screen onto that block.
The siblings used **none of it** — they ran the stock OSUI `LayoutSideMenu` (the
same layout the app already had) and got the shared look purely because **their
app theme inherited the shared theme**. The correct unification was a one-turn
base-theme change; the assumed one was four heavy, wedge-prone re-chroming turns,
two of them cancel/revert cycles.

**The tell that you guessed wrong:** the shell/layout adopts successfully but
renders **completely unstyled** (nav dumped as a full-width band) — the library
theme's CSS isn't loaded on that screen. That's not a bug to patch with more CSS;
it's the signal that chrome-by-block is the wrong integration axis and the
sibling pattern is theme inheritance. Revert and re-read the reference apps.

---

## Per-screen widget-type audit (before sign-off)

- [ ] Theme via ThemeValues / OSUI vars — no default green leak
- [ ] Header is `LayoutTopMenu` if design has app chrome
- [ ] Chips are `Tag` / `Badge`
- [ ] KPIs are `Counter`
- [ ] Search is `SearchInput`
- [ ] Form fields are native `Input` / `Text Area` / `Dropdown` / `Checkbox` (or OSUI `DropdownSearch` / `Switch` / `DatePicker`) — no hand-rolled controls
- [ ] Breadcrumbs use OSUI `Breadcrumb`
- [ ] Actions are `Button`; navigation is `Link`
- [ ] No reserved theme class names without prefix
- [ ] Labels are human-readable (no raw DB attribute names)
- [ ] Auth screens match theme

---

## Publish verification triad

After every publish — **never trust Mentor signals alone**:

1. **Live screenshot** (`mcp__preview__get_screenshot`) + optional `browser_*` drive.
2. **OML re-read** — `context_screens` / `context_actions` or follow-up read.
3. **Deploy proof** — `env_app` / `app_info` revision and **`modelDigest`** changed;
   `no_changes_detected: true` fires falsely on many tenants.

If `change_applied: true` but triad fails → treat as not persisted; re-attempt in a fresh mentor session if contaminated.

---

## Platform limits (ODC Reactive)

| Limit | Workaround |
|-------|------------|
| No `Split()` in server expressions | Client-side JS for delimited strings |
| Date inputs show time unless typed `Date` | Type attribute as `Date` |
| `EscapeContent=No` on Expression ignored | Small JS `innerHTML` container — trusted text only; model / user text → plain text (`outsystems-agentic-app`) |
| `EmptyValue=NullIdentifier()` → raw `"0"` in Dropdown | Data all-row + cleared EmptyValue, both together — `outsystems-ui-recipes` §5 (EmptyText is ignored) |
| Screen aggregates not reactive | `RefreshData`; reference filter var in aggregate |
| Input commits after `OnChange` | Read live DOM value before `RefreshData` or use Search pattern |

---

## Adversarial data checks (coordinate with tester)

- **Every stat/counter/badge/KPI is bound to a query, not a literal.** After a
  mockup-based build, sweep them all and confirm each *moves* when the data moves.
  An oddly specific value ("209,431 total") over a 219-row table is a design
  sample number that was never wired. Rebind per **outsystems-ui-recipes** §16.

- Same filter definition drives **KPI count and list count**.
- Filter flags actually constrain (e.g. `AnnualReview`).
- Dates use local `CurrDate()` — watch off-by-one.
- State-clearing actions clear dependent fields (e.g. `Reactivate` clears `Enddate`).
- Greeting/avatar from `GetUserId()` — never unfiltered aggregate first row.

---

## Claude Design `/design-sync` import set

When syncing a design system into Claude Design, import from this skill's `references/`:

- `references/outsystems-ui/ui-reference.md`, `styles-and-utilities.md`, `layouts.md`, `design-tokens.md`
- `references/screen-guides/design-system.md`
- the theme-collision and reserved-class-name rules in Skill `outsystems-css-theming`

Score each design direction against the widget-type table above before user selection.
