#!/usr/bin/env python3
"""The Implementation Report cites the spec's requirement ids, unchanged.

The extraction writes one id per requirement into `requirements.json`
(`REQ-001`, `BR-418`, `RULE-012`, `NFR-03`, ...), and the Business Spec uses the
same ids. A reader holds the report beside the spec and looks each id up, so an
id the report renumbers (`REQ-01`), respells (`REQ‑001` with a non-ASCII dash)
or drops can no longer be checked against the spec.

This compares the two, mechanically:

* every spec id has exactly one row in section 5 (the requirements list, one
  table), a row in appendix A (traceability) and a row in appendix Z (the
  requirements checklist, the report's last section);
* every id a section-5, appendix-A or appendix-Z row cites is a spec id or a
  report-local `IN-nn` id; under section 5's Additions subsection only ids the
  spec doesn't have are allowed;
* every section-5 and appendix-Z row has a plain-English Description cell;
* each appendix-Z row's Implemented / Tested answer matches its section-5
  status and verdict, and the `Implemented: X of N` / `Tested: Y of M` totals
  line matches the rows;
* no section-5 row merges two ids (an appendix-A row may trace several), and no
  id anywhere in the report is a respelling of a family spec id (`REQ-001`); a
  native id that isn't in the spec fails where a row cites it.

Spec ids keep whatever prefix the extraction gives them (`REQ-001`,
`PMODEL-ORD100-0001`, `MSACCESS-RULE-0007`) and are matched as whole tokens,
exactly as spelled. An id listed under an entry's `merged` was folded into that
entry: the entry's row covers it, and a row may cite either or both.

Usage:

    python3 check_report_ids.py <requirements.json> <report.md> [--business-spec <Customer>-Business-Spec.md]
                                [--spec <business-brief.md> ...]

`--business-spec` adds the ids the extractor's Business Spec numbers in its
section 5 table but `requirements.json` doesn't carry (some stacks number their
rules only there); they are spec ids like any other and need the same rows.

`--spec` adds the re-derived capability ids (`CAP-nn`) a Business Brief defines
beyond `requirements.json`, so the report may cite them too. It admits no other
family: the reporter writes the brief and the report in the same turn, so a
brief must not be able to legitimise an id the spec doesn't have.

Exit 1 on any mismatch, or with one FAIL line when an input file can't be
read. Standard library only, Python 3.8+.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

# The id families the extraction writes into requirements.json, plus the
# report-local IN- ids for an input without ids.
FAMILIES = ("REQ", "US", "FR", "CAP", "BR", "RULE", "NFR")
# Any dash-like character between prefix and number, or (for a known family
# written in capitals or title case) a space or nothing: a respelled id
# (`REQ‑001`, `Req 1`, `REQ001`) still has to be found to be flagged.
DASHES = "-‐‑‒–—―−"
# An id starts and ends where the token does: `MSACCESS-RULE-0002`, `REQ-001-v2`, `REQ-001a` and
# `PMODEL-ORD100-0001.v2` are other tokens, never `RULE-0002`, `REQ-001` or `PMODEL-ORD100-0001`.
# A dash or dot before or after the id still counts as punctuation when no word character follows it.
LEFT = r"(?<![" + DASHES + r"\w])(?<!\w\.)"
RIGHT = r"(?!\w)(?![" + DASHES + r".]\w)"
# A family id may follow a number and a dash, so a range (`REQ-01–REQ-02`) still shows both ends.
ANY_ID = re.compile(r"(?<!\w)(?<![A-Za-z][" + DASHES + r"])(?<!\w\.)([A-Za-z]{2,6})([" + DASHES + r"]| ?)([0-9]{1,4})"
                    + RIGHT)
LOCAL_ID = re.compile(r"^IN-[0-9]{2,}$")
# A Business Spec id outside the families above (`PMODEL-ORD100-0001`): one token with a digit.
SPEC_TOKEN = re.compile(r"^[A-Za-z][A-Za-z0-9]*(?:[-_.][A-Za-z0-9]+)+$")
# The appendix-Z answer each section-5 status and verdict maps to.
IMPLEMENTED = {"implemented, tested": "yes", "implemented, not tested": "yes", "changed": "yes",
               "partial": "partial", "deferred": "no", "not built": "no"}
TESTED = {"pass": "yes", "partial": "partial", "fail": "no", "not tested": "no", "not observable": "n/a"}
Z_TITLE = re.compile(r"^(?:appendix\s+)?Z(?:[.):]|\s|$)", re.I)
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
SEPARATOR_ROW = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
PIPE = re.compile(r"(?<!\\)\|")
# Addresses keep their own spelling and are not citations: a link's target
# (`](#req-001)`), a URL, an in-page anchor, or a file name (`shots/req-002.png`).
ADDRESS = re.compile(
    r"\]\([^)]*\)"
    r"|\b[A-Za-z][A-Za-z0-9+.-]*://\S+"
    r"|(?<![\w&])#[\w-]+"
    r"|[\w./-]*\.(?:png|jpe?g|gif|svg|webp|pdf|md|html?|json|csv|xlsx?|txt|docx?)\b",
    re.I,
)


def canonical(prefix: str, number: str) -> Tuple[str, int]:
    """The key two spellings of one id share: `REQ-01`, `req‑1` and `REQ-001` all match."""
    return prefix.upper(), int(number)


def find_ids(text: str) -> List[Tuple[str, Tuple[str, int]]]:
    """Every id-shaped token in `text`, as spelled, with its canonical key.

    Without a dash, only a known family in capitals or title case counts, so
    "for us 2 regions" or "item 3" is not an id.
    """
    found = []
    text = ADDRESS.sub(" ", text)
    # Markdown escapes (`REQ\\-001`) render as the plain character, so they spell the same id.
    for m in ANY_ID.finditer(plain(text)):
        prefix, sep, number = m.groups()
        if not sep or sep == " ":
            if prefix.upper() not in FAMILIES or not (prefix.isupper() or prefix.istitle()):
                continue
        found.append((m.group(0), canonical(prefix, number)))
    return found


def read(path: Path) -> str:
    """A text input, BOM-tolerant; ValueError, with a readable reason, when it can't be read."""
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError("{}: can't be read ({})".format(path.name, exc.strerror if isinstance(exc, OSError) else exc))


def spec_ids(requirements_path: Path) -> Tuple[List[str], Dict[str, str]]:
    """The spec's ids in order, and each folded (`merged`) id -> the id of the entry it folded into.

    ValueError, with a readable reason, when the file can't be used.
    """
    text = read(requirements_path)
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ValueError("{}: can't be read as JSON ({})".format(requirements_path.name, exc))
    name = requirements_path.name
    if isinstance(data, list):
        rows = data  # a bare list of requirement objects, as the extractor's reader also accepts
    elif isinstance(data, dict) and "requirements" in data:
        rows = data["requirements"]
    elif isinstance(data, dict) and isinstance(data.get("by_tier"), dict) and all(
            isinstance(tier, list) for tier in data["by_tier"].values()):
        rows = [r for tier in data["by_tier"].values() for r in tier]
    else:
        raise ValueError("{}: expected a list of requirement objects, a `requirements` list or a `by_tier` "
                         "mapping of lists".format(name))
    if not isinstance(rows, list):
        raise ValueError("{}: `requirements` is a {}, not a list of requirement objects".format(
            name, type(rows).__name__))
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"].strip():
            raise ValueError("{}: requirement {} has no `id` string".format(name, index + 1))
        merged = row.get("merged", [])
        if not isinstance(merged, list) or not all(isinstance(m, str) and m.strip() for m in merged):
            raise ValueError("{}: requirement {} has a `merged` that is not a list of id strings".format(
                name, row["id"]))
    ids = list(dict.fromkeys(row["id"] for row in rows))
    if not ids:
        # Certifying a report against nothing would read as a pass.
        raise ValueError("{}: lists no requirement ids, so there is nothing to check the report against".format(name))
    parent_of = {m: row["id"] for row in rows for m in row.get("merged", []) if m not in ids}
    return ids, parent_of


def defined_in(markdown: str) -> List[Tuple[str, Tuple[str, int]]]:
    """Ids a spec markdown file names in a known family, as spelled there, with their keys."""
    found = {}  # type: Dict[str, Tuple[str, int]]
    for line in strip_fences(markdown.splitlines()):
        for token, key in find_ids(line):
            if key[0] in FAMILIES:
                found.setdefault(token, key)
    return list(found.items())


def strip_fences(lines: Iterable[str]) -> List[str]:
    """Blank every line inside a fenced code block, keeping line numbers.

    A fence closes only on the opener's character, at least as long, with
    nothing after it, so a ```` block can show a ``` example (CommonMark).
    """
    out, opener = [], None  # type: List[str], Optional[str]
    for line in lines:
        m = FENCE.match(line)
        if opener is None:
            if m:
                opener = m.group(1)
            out.append("" if m else line)
            continue
        if m and m.group(1)[0] == opener[0] and len(m.group(1)) >= len(opener) and not m.group(2).strip():
            opener = None
        out.append("")
    return out


def cells(row: str) -> List[str]:
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [c.strip() for c in re.split(r"(?<!\\)\|", row)]


def table_rows(lines: List[str]) -> Tuple[Dict[int, int], Dict[int, List[str]]]:
    """Line number -> table number for every GFM table body row, with or without leading pipes,
    and table number -> its lower-cased header cells.

    A table starts at a header line with a pipe followed by a separator row, and
    runs until a line without an unescaped pipe.
    """
    rows = {}  # type: Dict[int, int]
    headers = {}  # type: Dict[int, List[str]]
    inside, table = False, 0
    for no, line in enumerate(lines, 1):
        text = line.strip()
        if inside and PIPE.search(text) and not HEADING.match(text):
            rows[no] = table
            continue
        inside = (no >= 2 and PIPE.search(text) is not None and SEPARATOR_ROW.match(text) is not None
                  and PIPE.search(lines[no - 2].strip()) is not None)
        table += inside
        if inside:
            headers[table] = [visible(c).lower() for c in cells(lines[no - 2])]
    return rows, headers


def column(header: List[str], name: str) -> Optional[int]:
    """The index of the first header cell that starts with `name`, or None."""
    return next((i for i, h in enumerate(header) if re.sub(r"[`*_]", "", h).startswith(name)), None)


def plain(cell: str) -> str:
    """A cell as it renders: no emphasis or code marks, no inline HTML (a status badge), no escapes.

    Underscore emphasis (`_x_`, `__x__`) goes only where it opens and closes at a word's edge, so
    an underscore inside an id (`LP_C_FOUTR`, `ORD_CHK`) stays.
    """
    text = re.sub(r"(?<!\w)(__?)(?=\S)(.+?)(?<=\S)\1(?!\w)", r"\2", re.sub(r"[`*]|<[^>]*>", "", cell))
    return re.sub(r"\\(.)", r"\1", text).strip()


def visible(cell: str) -> str:
    """The text a reader sees in a cell: a link's label without its target, as rendered."""
    return re.sub(r"[\[\]]", " ", plain(ADDRESS.sub(" ", cell))).strip()


def ids_in_cell(cell: str) -> List[str]:
    return [token for token, _ in find_ids(cell)]


class Row:
    def __init__(self, line_no: int, ids: List[str], addition: bool, table: int, row_cells: List[str]) -> None:
        self.line_no = line_no
        self.ids = ids
        self.addition = addition
        self.table = table
        self.cells = row_cells
        self.first = row_cells[0]

    def cell(self, index: Optional[int]) -> str:
        """A cell as the reader sees it: a link counts by its label, never by its target."""
        return visible(self.cells[index]) if index is not None and index < len(self.cells) else ""


def section_rows(lines: List[str], section: str, body_rows: Dict[int, int]) -> Optional[List[Row]]:
    """Table body rows of a `##` section whose number is `section`, or None when the section is absent.

    Each row carries the ids its first cell names (none for an unnumbered row) and
    its table; rows under a `###` heading that mentions "Addition" are flagged as additions.
    """
    rows = []  # type: List[Row]
    found, inside = False, False
    addition_level = 0  # the level of the open Additions heading, 0 when none is open
    pattern = re.compile(r"^(?:appendix\s+|section\s+)?" + re.escape(section) + r"(?:[.):]|\s|$)", re.I)
    for no, line in enumerate(lines, 1):
        h = HEADING.match(line)
        if h:
            level, title = len(h.group(1)), h.group(2).strip()
            if level <= 2:
                inside = level == 2 and bool(pattern.match(title))
                found = found or inside
                addition_level = 0
            elif inside and (not addition_level or level <= addition_level):
                # A heading nested under Additions stays inside it; a sibling or parent ends it.
                addition_level = level if "addition" in title.lower() else 0
            continue
        if not inside or no not in body_rows:
            continue
        row_cells = cells(line)
        rows.append(Row(no, ids_in_cell(visible(row_cells[0])), bool(addition_level), body_rows[no], row_cells))
    return rows if found else None


def is_spec_token(text: str) -> bool:
    """A native id shape (`PMODEL-ORD100-0001`, `MSACCESS-RULE-0007`): one token with a digit."""
    return bool(SPEC_TOKEN.match(text)) and re.search(r"[0-9]", text) is not None


def business_spec_ids(path: Path, requirements: Path) -> List[str]:
    """The ids the first cell of an extractor Business Spec's section-5 `| ID | ...` table rows names, in order.

    ValueError when the file isn't one: a Business Brief (it would turn the reporter's own ids into
    spec ids), a file outside the spec collection, or one with no section-5 `ID` table, such as a
    split application's overview (pass each domain's Business Spec and the application-wide one).
    """
    home = requirements.resolve().parent
    where = path.resolve().parent
    if path.name.lower().endswith("-business-brief.md"):
        raise ValueError("{}: is a Business Brief, not the extractor's Business Spec; pass it with --spec".format(
            path.name))
    if where != home and where.parent != home / "domains":
        raise ValueError("{}: is not in the spec collection beside {} (or under its domains/), so it isn't the "
                         "extractor's Business Spec".format(path.name, requirements.name))
    lines = strip_fences(read(path).splitlines())
    body_rows, headers = table_rows(lines)
    rows = [row for row in section_rows(lines, "5", body_rows) or []
            if re.sub(r"[`*_]", "", headers.get(row.table, [""])[0]).strip() == "id"]
    if not rows:
        raise ValueError("{}: has no section-5 table headed ID, so it numbers no requirements; for a split "
                         "application pass each domain's Business Spec and Business-Spec-application-wide.md, "
                         "not the overview".format(path.name))
    return list(dict.fromkeys(visible(row.first) for row in rows if is_spec_token(visible(row.first))))


def last_section(lines: List[str]) -> str:
    """The title of the report's last `#`/`##` heading."""
    titles = [h.group(2) for h in map(HEADING.match, lines) if h and len(h.group(1)) <= 2]
    return titles[-1] if titles else ""


def check(requirements: Path, report: Path, specs: Iterable[Path] = (),
          business_specs: Iterable[Path] = ()) -> Tuple[List[str], str]:
    problems = []  # type: List[str]
    try:
        expected, parent_of = spec_ids(requirements)
        for business_spec in business_specs:
            expected += [rid for rid in business_spec_ids(business_spec, requirements)
                         if rid not in expected and rid not in parent_of]
    except ValueError as exc:
        return [str(exc)], ""
    by_key = {}  # type: Dict[Tuple[str, int], str]
    for rid in list(expected) + list(parent_of):
        found = find_ids(rid)
        # Only an id that is one family token as a whole (`REQ-001`) has respellings to catch;
        # `MSACCESS-RULE-0001` merely contains `RULE-0001`.
        if len(found) == 1 and found[0][0] == rid:
            by_key.setdefault(found[0][1], rid)
    known_set = set(expected) | set(parent_of)
    expected_set = set(expected)
    # Every spec id, whatever its prefix, is matched first as a whole token, exactly as spelled.
    spelled = re.compile(LEFT + "(?:" + "|".join(
        re.escape(rid) for rid in sorted(known_set, key=len, reverse=True)) + ")" + RIGHT)
    try:
        for spec in specs:
            # A brief adds only capability ids of its own (CAP-nn); any other family, or a
            # respelling of a spec id it quotes, is not the spec's and stays unknown.
            for token, key in defined_in(read(spec)):
                if key[0] == "CAP" and key not in by_key:
                    by_key[key] = token
                    known_set.add(token)
        lines = strip_fences(read(report).splitlines())
    except ValueError as exc:
        return [str(exc)], ""
    name = report.name
    body_rows, headers = table_rows(lines)

    def classify(token: str) -> Optional[str]:
        """Why a cited id is wrong, or None when it is a spec or report-local id."""
        if token in known_set or LOCAL_ID.match(token):
            return None
        found = find_ids(token)
        twin = by_key.get(found[0][1]) if found and found[0][0] == token else None
        if twin:
            return "respells spec id {} as {}".format(twin, token)
        return "cites {}, which is not in the spec{}".format(
            token, "" if found else " (if the Business Spec numbers it, pass --business-spec)")

    def native_ids(cell: str) -> List[str]:
        """Id-shaped tokens no family pattern reads as a whole (an unknown `MSACCESS-RULE-0099`)."""
        return [t for t in re.findall(r"[A-Za-z][\w.-]*[A-Za-z0-9]", ADDRESS.sub(" ", cell))
                if is_spec_token(t) and [tok for tok, _ in find_ids(t)] != [t]]

    # Rows whose first cell is checked here; the prose scan below reads their other cells.
    row_lines = set()  # type: Set[int]
    spec_rows = {}  # type: Dict[str, Dict[str, Row]]
    for label, section in (("section 5", "5"), ("appendix A", "A"), ("appendix Z", "Z")):
        rows = section_rows(lines, section, body_rows)
        if rows is None:
            problems.append("{}: no {} heading (`## {}. ...`)".format(name, label, section))
            continue
        for row in rows:
            # Only what the reader sees counts: a link's target or an anchor is an address, not a citation.
            first = visible(row.first)
            row.ids = spelled.findall(first) + ids_in_cell(spelled.sub(" ", first))
        # An unknown native id is a citation only in a requirements table: one headed by an id
        # column, or one that already cites a known id. Another table's first column is just text.
        cites = {row.table for row in rows if row.ids} | {
            row.table for row in rows if re.search(r"\bids?\b", re.sub(r"[`*_]", "", headers.get(row.table, [""])[0]))}
        for row in rows:
            if row.table in cites:
                row.ids += native_ids(spelled.sub(" ", visible(row.first)))
        seen = {}  # type: Dict[str, int]
        spec_rows[section] = {}
        # The requirements and traceability tables are the ones whose rows cite ids; another
        # table in the section (a per-app summary, say) has none and isn't checked row by row.
        id_tables = {row.table for row in rows if row.ids}
        listed = sorted({row.table for row in rows if row.ids and not row.addition})
        if section != "A" and len(listed) > 1:
            problems.append("{}: {} splits the spec ids over {} tables; keep every id in one list".format(
                name, label, len(listed)))
        described = set()  # type: Set[int]
        for row in rows:
            if not row.ids:
                if row.table in id_tables and not row.addition:
                    problems.append("{}:{} ({}): a row with no spec id ({}); every row cites one, or sits under "
                                    "Additions".format(name, row.line_no, label, row.first or "empty"))
                continue
            row_lines.add(row.line_no)
            where = "{}:{} ({})".format(name, row.line_no, label)
            if section != "A" and not row.addition:
                index = column(headers.get(row.table, []), "description")
                if index is None:
                    if row.table not in described:
                        problems.append("{}: the table has no Description column; every requirement says in plain "
                                        "English what it is".format(where))
                    described.add(row.table)
                # An id, any id, says what the requirement is no better than a blank does.
                elif not re.sub(r"[\W_]", "", " ".join(
                        t for t in re.findall(r"\S+", row.cell(index)) if not is_spec_token(t.strip(".,;:()")))):
                    problems.append("{}: {} has no description".format(where, row.ids[0]))
            # A folded id stands for the entry it folded into, so a row may list it beside its parent.
            if len({parent_of.get(token, token) for token in row.ids}) > 1 and section != "A":
                problems.append("{}: one row merges {}; give each id its own row".format(where, ", ".join(row.ids)))
            for token in row.ids:
                rid = parent_of.get(token, token)
                if row.addition:
                    # An addition is work the spec didn't ask for: a spec id, or a respelling of one, isn't one.
                    if rid in expected_set:
                        problems.append("{}: {} is a spec id; it belongs in the requirements list, not under Additions"
                                        .format(where, token))
                    else:
                        why = classify(token)
                        if why and why.startswith("respells"):
                            problems.append("{}: {}".format(where, why))
                    continue
                why = classify(token)
                if why:
                    problems.append("{}: {}".format(where, why))
                    continue
                if section != "A" and seen.get(rid, row.line_no) != row.line_no:
                    problems.append("{}: {} already has a row at line {}".format(
                        where, token if rid == token else "{} (folded into {})".format(token, rid), seen[rid]))
                seen.setdefault(rid, row.line_no)
                spec_rows[section].setdefault(rid, row)
        missing = [rid for rid in expected if rid not in seen]
        if missing:
            shown = ", ".join(missing[:20]) + (" and {} more".format(len(missing) - 20) if len(missing) > 20 else "")
            problems.append("{}: {} of {} spec ids have no {} row: {}".format(
                name, len(missing), len(expected), label, shown))
    if "Z" in spec_rows:
        problems += checklist(name, lines, headers, spec_rows.get("5", {}), spec_rows["Z"], expected_set)

    # Prose, captions, other tables and a row's other cells: a respelled id anywhere still breaks the lookup.
    for no, line in enumerate(lines, 1):
        # Addresses go first, so blanking an id inside a URL can't leave a piece of it to read as prose.
        text = spelled.sub(" ", ADDRESS.sub(" ", "|".join(cells(line)[1:]) if no in row_lines else line))
        for token, key in sorted(set(find_ids(text))):
            twin = by_key.get(key)
            if twin and token not in known_set:
                problems.append("{}:{}: respells spec id {} as {}".format(name, no, twin, token))

    summary = ("{} spec ids{}, each with one described section-5 row, an appendix-A row and a matching appendix-Z "
               "checklist row, spelled as the spec spells them").format(
        len(expected), " (plus {} folded into them)".format(len(parent_of)) if parent_of else "")
    return problems, summary


def checklist(name: str, lines: List[str], headers: Dict[int, List[str]], listed: Dict[str, Row],
              ticked: Dict[str, Row], spec: Set[str]) -> List[str]:
    """Appendix Z closes the report, lists exactly the section-5 rows, and each answer and the totals agree."""
    problems = []  # type: List[str]
    if not Z_TITLE.match(last_section(lines)):
        problems.append("{}: appendix Z (the requirements checklist) must be the report's last section".format(name))
    # Spec ids missing from either side are already reported; this catches IN-nn and CAP-nn rows.
    for rid in listed:
        if rid not in ticked and rid not in spec:
            problems.append("{}:{} (section 5): {} has no appendix Z row; the checklist lists every requirement in "
                            "section 5".format(name, listed[rid].line_no, rid))
    for rid in ticked:
        if rid not in listed and rid not in spec:
            problems.append("{}:{} (appendix Z): {} has no section-5 row; the checklist only restates section 5"
                            .format(name, ticked[rid].line_no, rid))
    counts = {"implemented": [0, 0], "tested": [0, 0]}  # type: Dict[str, List[int]]
    unreadable = set()  # type: Set[Tuple[int, str]]
    for rid, row in ticked.items():
        where = "{}:{} (appendix Z)".format(name, row.line_no)
        source = listed.get(rid)
        for answer_col, status_col, mapping, allowed in (("implemented", "status", IMPLEMENTED, "Yes, Partial or No"),
                                                         ("tested", "tested", TESTED, "Yes, Partial, No or n/a")):
            index = column(headers.get(row.table, []), answer_col)
            if index is None:
                problems.append("{}: the checklist has no {} column".format(where, answer_col.capitalize()))
                continue
            answer = row.cell(index).lower()
            if answer not in set(mapping.values()):
                problems.append("{}: {} {} is {!r}; answer {}".format(where, rid, answer_col, row.cell(index), allowed))
                continue
            counts[answer_col][0] += answer == "yes"
            counts[answer_col][1] += answer != "n/a"
            if not source:
                continue
            index = column(headers.get(source.table, []), status_col)
            if index is None:
                if (source.table, status_col) not in unreadable:
                    problems.append("{}:{} (section 5): the requirements table has no {} column, so the checklist "
                                    "can't be checked against it".format(name, source.line_no, status_col.capitalize()))
                unreadable.add((source.table, status_col))
                continue
            want = leading_term(source.cell(index), mapping)
            if want is None:
                problems.append("{}:{} (section 5): {} {} is {!r}, not one of: {}".format(
                    name, source.line_no, rid, status_col, source.cell(index),
                    ", ".join(sorted({k.upper() if mapping is TESTED else k.capitalize() for k in mapping}))))
            elif want != answer:
                problems.append("{}: {} {} says {} but its section-5 row says {}".format(
                    where, rid, answer_col, row.cell(index), want.capitalize() if want != "n/a" else want))
    prose, inside = [], False  # type: List[str], bool
    for line in lines:
        h = HEADING.match(line)
        if h and len(h.group(1)) <= 2:
            inside = bool(Z_TITLE.match(h.group(2)))
        elif inside and not PIPE.search(line):
            prose.append(line)
    m = re.search(r"\bImplemented:\s*([0-9]+) of ([0-9]+)\W+Tested:\s*([0-9]+) of ([0-9]+)",
                  visible(" ".join(prose)), re.I)
    if not m:
        problems.append("{}: appendix Z has no `Implemented: X of N. Tested: Y of M.` totals line".format(name))
        return problems
    for key, said in (("implemented", m.group(1, 2)), ("tested", m.group(3, 4))):
        if tuple(map(int, said)) != tuple(counts[key]):
            problems.append("{}: appendix Z says {} {} of {}, but its rows count {} of {}".format(
                name, key, said[0], said[1], *counts[key]))
    return problems


def leading_term(cell: str, vocabulary: Dict[str, str]) -> Optional[str]:
    """The mapped value of the vocabulary term a cell starts with; a reason may follow it (`PARTIAL (one region)`)."""
    text = re.sub(r"\s+", " ", cell.lower()).strip()
    for term in sorted(vocabulary, key=len, reverse=True):
        if text == term or (text.startswith(term) and not text[len(term)].isalnum()):
            return vocabulary[term]
    return None


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("requirements", type=Path, help="the extraction's requirements.json")
    parser.add_argument("report", type=Path, help="the Implementation Report markdown")
    parser.add_argument("--spec", type=Path, action="append", default=[],
                        help="a Business Brief whose re-derived CAP-nn ids the report may cite")
    parser.add_argument("--business-spec", type=Path, action="append", default=[],
                        help="the extractor's Business Spec; ids its section-5 table numbers are spec ids too")
    args = parser.parse_args(argv)
    problems, summary = check(args.requirements, args.report, args.spec, args.business_spec)
    for p in problems:
        print("FAIL " + p)
    if problems:
        if summary:  # empty when an input file itself couldn't be read
            print("{} mismatch(es) between the spec and the report".format(len(problems)))
        return 1
    print("OK " + summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
