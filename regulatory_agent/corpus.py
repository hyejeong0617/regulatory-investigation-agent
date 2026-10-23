"""HTML provenance, legal provision segmentation, and lossless table grids.

Only local files are read. No scripts, styles, or remote links are executed.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

from .util import clean, digest


@dataclass(eq=False)
class Node:
    tag: str
    attrs: dict[str, str]
    line: int
    children: list = field(default_factory=list)
    parent: "Node | None" = None

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.walk()

    def text(self) -> str:
        if self.tag in {"script", "style", "head"}:
            return ""
        chunks = []
        for child in self.children:
            if isinstance(child, str):
                chunks.append(child)
            else:
                chunks.append(child.text())
                if child.tag in {"p", "div", "tr", "td", "th", "br", "li"}:
                    chunks.append(" ")
        return clean("".join(chunks))


class DOM(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "wbr"}

    def __init__(self, html: str):
        super().__init__(convert_charrefs=True)
        self.root = Node("root", {}, 1)
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, dict(attrs), self.getpos()[0], parent=self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


@dataclass
class Evidence:
    id: str
    document: str
    regulation: str
    snapshot: str
    source_sha256: str
    location: str
    kind: str
    anchor: str
    line_start: int
    line_end: int
    text: str
    source_url: str
    links: list[str] = field(default_factory=list)
    table: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def table_grid(table: Node) -> list[dict]:
    """Expand spans, keeping each cell's original line and span origin."""
    rows = []
    for node in table.walk():
        if node.tag != "tr":
            continue
        ancestor = node.parent
        while ancestor and ancestor.tag != "table":
            ancestor = ancestor.parent
        if ancestor is table:
            rows.append(node)
    occupied: dict[tuple[int, int], dict] = {}
    result = []
    width = 0
    for r, row in enumerate(rows):
        c = 0
        for node in row.children:
            if not isinstance(node, Node) or node.tag not in {"td", "th"}:
                continue
            while (r, c) in occupied:
                c += 1
            rs = max(1, min(int(node.attrs.get("rowspan", "1")), 1000))
            cs = max(1, min(int(node.attrs.get("colspan", "1")), 50))
            cell = {"text": node.text(), "line": node.line, "origin_row": r + 1,
                    "origin_column": c + 1, "rowspan": rs, "colspan": cs,
                    "header": node.tag == "th" or "bold" in node.attrs.get("style", "")}
            for rr in range(r, r + rs):
                for cc in range(c, c + cs):
                    if (rr, cc) in occupied:
                        raise ValueError(f"Overlapping table cells at HTML line {node.line}")
                    occupied[rr, cc] = cell
            c += cs
            width = max(width, c)
        result.append({"row": r + 1, "line": row.line, "node": row})
    for r, row in enumerate(result):
        row["cells"] = [occupied.get((r, c), {"text": "", "line": row["line"],
                         "origin_row": r + 1, "origin_column": c + 1,
                         "rowspan": 1, "colspan": 1, "header": False}) for c in range(width)]
    return result


def row_text(row: dict) -> str:
    return " | ".join(f"C{i + 1}: {cell['text']}" for i, cell in enumerate(row["cells"]))


def _links(node: Node) -> list[str]:
    return list(dict.fromkeys(n.attrs["href"] for n in node.walk() if n.attrs.get("href")))


def parse_document(path: Path) -> tuple[dict, list[Evidence]]:
    raw = path.read_bytes()
    root = DOM(raw.decode("utf-8-sig")).root
    nodes = list(root.walk())
    canonical = next((n.attrs.get("href", "") for n in nodes
                      if n.tag == "link" and n.attrs.get("rel") == "canonical"), "")
    match = re.search(r"EU_(\d{4})_+(\d+)", path.name)
    regulation = f"{match[1]}/{int(match[2])}" if match else path.stem
    # Pre-2015 acts often use number/year, as printed in the legal title.
    for n in nodes:
        if n.tag == "p" and "REGULATION" in n.text():
            printed = re.search(r"REGULATION\s+\([A-Z]+\)\s+(?:No\s+)?(\d+/\d+)", n.text())
            if printed:
                regulation = printed[1]
                break
    match = re.search(r"\d{4}-\d{2}-\d{2}", path.name)
    snapshot = match[0] if match else "original act (not consolidated)"
    source_hash = digest(raw)
    ids = {n.attrs["id"]: n for n in nodes if n.attrs.get("id")}
    records: list[Evidence] = []
    section = "Preamble"
    anchor = ""
    pending: list[Node] = []
    table_number = 0
    section_titles: list[str] = []

    def footnotes(links):
        texts = []
        for link in links:
            if link.startswith("#") and link[1:] in ids:
                target = ids[link[1:]]
                # Never append a whole Article/Annex as a 'footnote'.
                if re.match(r"^(?:Article|ANNEX)\b", target.text()):
                    continue
                while target.parent and target.tag not in {"p", "tr"} and not (
                    target.tag == "div" and "tbl-norm" in target.attrs.get("class", "")):
                    target = target.parent
                value = target.text()
                if value and len(value) <= 4500 and ("foot" in target.attrs.get("class", "") or re.match(r"^\(\s*\d+\s*\)", value)):
                    texts.append(f"Footnote {link}: {value}")
        return list(dict.fromkeys(texts))

    def add(location, kind, text, elements, table=None):
        links = list(dict.fromkeys(link for n in elements for link in _links(n)))
        notes = footnotes(links)
        if notes:
            text += "\n" + "\n".join(notes)
        lines = [n.line for element in elements for n in element.walk()]
        record_anchor = next((n.attrs["id"] for n in elements if n.attrs.get("id")), anchor)
        identity = f"{source_hash}|{location}|{min(lines)}|{text}"
        records.append(Evidence(
            id="E" + digest(identity.encode())[:16], document=path.name,
            regulation=regulation, snapshot=snapshot, source_sha256=source_hash,
            location=location, kind=kind, anchor=record_anchor,
            line_start=min(lines), line_end=max(lines), text=text,
            source_url=canonical + ("#" + record_anchor if record_anchor else ""),
            links=links, table=table))

    def flush():
        nonlocal pending
        if not pending:
            return
        # Split on complete source paragraphs; never remove subparagraph labels.
        batches, batch, size = [], [], 0
        for p in pending:
            if batch and size + len(p.text()) > 4200:
                batches.append(batch)
                batch, size = [], 0
            batch.append(p)
            size += len(p.text())
        if batch:
            batches.append(batch)
        for i, batch in enumerate(batches):
            label = section + (f" / part {i + 1} of {len(batches)}" if len(batches) > 1 else "")
            add(label, "provision", "\n".join(dict.fromkeys([section] + [p.text() for p in batch])), batch)
        pending = []

    def parse_table(table):
        nonlocal table_number
        table_number += 1
        rows = table_grid(table)
        headers = []
        for row in rows:
            cells = row["cells"]
            # Section/header rows in EUR-Lex use bold cells or an empty first cell.
            is_header = any(c["header"] for c in cells) or (
                not cells[0]["text"] and any("boldface" in n.attrs.get("class", "") for n in row["node"].walk()))
            if is_header:
                # A new numbered contaminant subsection supersedes previous columns.
                if re.fullmatch(r"\d+(?:\.\d+)?", cells[0]["text"]):
                    depth = cells[0]["text"].count(".")
                    if depth:
                        headers = headers[:1]
                    else:
                        headers = []
                headers.append(row)
                headers = headers[-5:]
            row["headers"] = list(headers)

        # Preserve visually grouped import entries. Some frozen HTML has blank
        # hazard cells and the hazard/frequency only in the middle of the block.
        # Do NOT forward-fill: keep complete raw block context and its provenance.
        country_col = next((i for row in rows[:5] for i, c in enumerate(row["cells"])
                            if "country of origin" in c["text"].lower()), None)
        product_col = next((i for row in rows[:5] for i, c in enumerate(row["cells"])
                            if "food and feed" in c["text"].lower()), None)
        contexts: dict[int, list] = {}
        if country_col is not None and product_col is not None:
            groups: dict[int, list] = {}
            for row in rows[1:]:
                groups.setdefault(row["cells"][country_col]["origin_row"], []).append(row)
            for group in groups.values():
                block = []
                for row in group:
                    block.append(row)
                    product = row["cells"][product_col]["text"]
                    if re.fullmatch(r"\(?\s*(?:Food|Feed|Food and feed)\s*\)?", product, re.I):
                        for member in block:
                            contexts[member["row"]] = list(block)
                        block = []
                if block:
                    for member in block:
                        contexts[member["row"]] = list(block)
        for row in rows:
            row_id = row["cells"][0]["text"]
            label = f"{section} / table {table_number} / HTML row {row['row']}"
            if re.fullmatch(r"\d+(?:\.\d+)*", row_id):
                label += f" / entry {row_id}"
            context_rows = contexts.get(row["row"], [])
            # Include every nonblank hazard/frequency sibling with its original
            # row number, not a guessed assignment to the selected product.
            context_summary = []
            if len(context_rows) > 1:
                for sibling in context_rows:
                    cells = sibling["cells"]
                    if any(c["text"] for c in cells[-2:]):
                        context_summary.append(f"HTML row {sibling['row']}: {row_text(sibling)}")
            text = section + "\n"
            if row["headers"]:
                text += "Table headers:\n" + "\n".join(row_text(h) for h in row["headers"]) + "\n"
            text += f"HTML row {row['row']}: {row_text(row)}"
            if context_summary:
                text += "\nSource block context (blank cells are not inferred; verify applicability across rows):\n" + "\n".join(context_summary)
            relevant = list(dict.fromkeys([h["node"] for h in row["headers"]] + [row["node"]] + [s["node"] for s in context_rows]))
            table_meta = {"table_number": table_number, "row_number": row["row"],
                          "cells": row["cells"], "headers": [row_text(h) for h in row["headers"]],
                          "context_row_numbers": [r["row"] for r in context_rows],
                          "context": context_summary,
                          "blank_cells_inferred": False}
            add(label, "table_row", text, relevant, table_meta)

    def visit(node):
        nonlocal section, anchor
        if node.tag in {"head", "script", "style"}:
            return
        classes = node.attrs.get("class", "").split()
        if node.tag == "table" and ("borderOj" in classes or node.attrs.get("border") == "1"):
            flush()
            parse_table(node)
            return
        if node.tag == "p" or node.tag in {"h1", "h2", "h3"} or (
            node.tag == "div" and "norm" in classes):
            value = node.text()
            if not value:
                return
            heading = re.fullmatch(r"Article\s+\d+[a-z]?|ANNEX(?:\s+[IVXLCDM]+[a-z]?)?", value, re.I)
            if heading:
                flush()
                section = value
                section_titles.append(value)
                anchor = node.attrs.get("id", "")
                if not anchor and node.parent:
                    anchor = node.parent.attrs.get("id", "")
            if any("arrow" == c or c == "modref" for c in classes):
                return
            pending.append(node)
            return
        for child in node.children:
            if isinstance(child, Node):
                visit(child)

    visit(root)
    flush()
    title = next((n.text() for n in nodes if "eli-main-title" in n.attrs.get("class", "")), "")
    if not title:
        title = next((n.text() for n in nodes if n.tag == "p" and "REGULATION" in n.text() and len(n.text()) < 1200), regulation)
    manifest = {"file": path.name, "bytes": len(raw), "sha256": source_hash,
                "regulation": regulation, "snapshot": snapshot, "canonical_url": canonical,
                "title": title, "provisions": list(dict.fromkeys(section_titles)), "records": len(records)}
    return manifest, records


class Corpus:
    def __init__(self, source_dir: Path):
        paths = sorted(source_dir.glob("*.html"))
        if not paths:
            raise ValueError(f"No HTML source documents found in {source_dir}")
        self.source_dir = source_dir.resolve()
        self.manifest = []
        self.records: list[Evidence] = []
        for path in paths:
            manifest, records = parse_document(path)
            if not records:
                raise ValueError(f"No legal text parsed from {path.name}")
            self.manifest.append(manifest)
            self.records.extend(records)
        self.by_id = {r.id: r for r in self.records}
        if len(self.by_id) != len(self.records):
            raise ValueError("Evidence ID collision")
        self.fingerprint = digest("".join(m["sha256"] for m in self.manifest).encode())

    def catalog(self):
        return [{k: m[k] for k in ("file", "regulation", "snapshot", "title", "provisions")} for m in self.manifest]

    def lookup(self, regulation: str, location: str, limit: int = 12):
        if not regulation or not location:
            return []
        pattern = re.compile(r"^" + re.escape(clean(location)) + r"(?:$|\s*/)", re.I)
        return [r for r in self.records if r.regulation == regulation and pattern.search(r.location)][:limit]

    def neighbors(self, evidence_id: str, radius: int = 2):
        record = self.by_id.get(evidence_id)
        if record is None:
            return []
        i = self.records.index(record)
        return [r for r in self.records[max(0, i-radius):i+radius+1] if r.document == record.document]

    def linked(self, evidence_id: str):
        record = self.by_id.get(evidence_id)
        if record is None:
            return []
        anchors = {link[1:] for link in record.links if link.startswith("#")}
        return [r for r in self.records if r.document == record.document and r.anchor in anchors][:12]
