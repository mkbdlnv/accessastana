"""Build the final deliverables from the Markdown drafts and project artefacts.

    uv run --group docs python docs/final/build.py            # budget.xlsx + DOCX + PPTX (+ PDFs for review)
    uv run --group docs python docs/final/build.py --no-pdf   # skip the LibreOffice conversion

Outputs (docs/final/):
- budget/budget.xlsx, budget/budget_tables.md  (docs/final/budget/budget_model.py)
- Пояснительная_записка_AccessAstana.docx       (python-docx, ГОСТ 7.32-2017 layout)
- Презентация_AccessAstana.pptx                 (python-pptx, 16:9, speaker notes)
- _review/*.pdf                                 (LibreOffice render, for visual QA; not a deliverable)

Table of contents: python-docx cannot compute page numbers, so the DOCX is built
twice. Pass 1 has a TOC of the same size with dummy numbers; it is rendered to PDF,
heading pages are read with `pdftotext`, and pass 2 writes them into the cached
result of a real Word TOC field (Word refreshes it on open: updateFields).
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Emu, Mm, Pt, RGBColor
from PIL import Image

HERE = Path(__file__).resolve().parent
NOTE_MD = HERE / "explanatory_note.md"
SLIDES_MD = HERE / "presentation_outline.md"
DOCX_OUT = HERE / "Пояснительная_записка_AccessAstana.docx"
PPTX_OUT = HERE / "Презентация_AccessAstana.pptx"
REVIEW = HERE / "_review"
FONT = "Times New Roman"
TEXT_W_MM = 210 - 30 - 15  # A4 minus left/right margins (ГОСТ 7.32: 30 / 15 mm)
PLACEHOLDER_RE = re.compile(r"\[(ЗАПОЛНИТЬ|НУЖЕН ИСТОЧНИК)[^\]]*\]")


# =============================================================================================== Markdown
def read_md(path: Path) -> list[str]:
    """Lines of `path` with <!-- include: x --> expanded. Included files lose their
    first H1 (the appendix heading replaces it); their headings are demoted by two
    levels, and image paths are made absolute."""
    out: list[str] = []
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"<!--(?!\s*(include|toc|title|/title)\b).*?-->", "", text, flags=re.S)  # drop comments
    for line in text.splitlines():
        m = re.match(r"\s*<!--\s*include:\s*(.+?)\s*-->", line)
        if m:
            inc = (path.parent / m.group(1)).resolve()
            sub = read_md(inc)
            first_h1 = next((i for i, s in enumerate(sub) if s.startswith("# ")), None)
            if first_h1 is not None:
                del sub[first_h1]
            for s in sub:
                if re.match(r"#{1,3} ", s):
                    s = "##" + s  # demote: '# x' → '### x'
                out.append(s)
            continue
        out.append(_abs_images(line, path.parent))
    return out


def _abs_images(line: str, base: Path) -> str:
    def repl(m: re.Match[str]) -> str:
        p = Path(m.group(2))
        return f"![{m.group(1)}]({(base / p).resolve() if not p.is_absolute() else p})"

    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", repl, line)


@dataclass
class Block:
    kind: str  # title | h1 | h2 | h3 | p | bullet | number | quote | table | image | formula | code | toc
    text: str = ""
    rows: list[list[str]] = field(default_factory=list)
    caption: str | None = None
    lines: list[str] = field(default_factory=list)


def parse(lines: list[str]) -> list[Block]:
    blocks: list[Block] = []
    i, para, pending_caption = 0, [], None

    def flush() -> None:
        nonlocal para
        if para:
            blocks.append(Block("p", " ".join(s.strip() for s in para)))
            para = []

    while i < len(lines):
        line = lines[i].rstrip()
        s = line.strip()
        if s == "<!-- title -->":
            flush()
            j = lines.index("<!-- /title -->", i)
            blocks.append(Block("title", lines=lines[i + 1 : j]))
            i = j + 1
            continue
        if s == "<!-- toc -->":
            flush()
            blocks.append(Block("toc"))
        elif s.startswith("```"):
            flush()
            kind = "formula" if s[3:].strip() == "formula" else "code"
            j = i + 1
            body = []
            while j < len(lines) and not lines[j].strip().startswith("```"):
                body.append(lines[j].rstrip())
                j += 1
            blocks.append(Block(kind, lines=[b for b in body if b.strip()]))
            i = j
        elif m := re.match(r"(#{1,6}) (.+)", s):
            flush()
            level = len(m.group(1))
            blocks.append(Block({1: "h1", 2: "h2"}.get(level, "h3"), m.group(2).strip()))
        elif (m := re.fullmatch(r"\*\*(Таблица [^—]+ — .+)\*\*", s)) and i + 2 < len(lines) and \
                lines[i + 2].strip().startswith("|"):
            flush()
            pending_caption = "!" + m.group(1)  # '!' = explicit label, not auto-numbered
        elif s.startswith("Таблица:"):
            flush()
            pending_caption = s.removeprefix("Таблица:").strip()
        elif s.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                raw = lines[i].strip().strip("|").replace("\\|", "\x00")  # keep escaped pipes
                cells = [c.strip().replace("\x00", "|") for c in raw.split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                    rows.append(cells)
                i += 1
            blocks.append(Block("table", rows=rows, caption=pending_caption))
            pending_caption = None
            continue
        elif m := re.match(r"!\[([^\]]*)\]\(([^)]+)\)", s):
            flush()
            blocks.append(Block("image", m.group(2), caption=m.group(1)))
        elif line.startswith((" ", "\t")) and re.match(r"[-*] ", s) and blocks and blocks[-1].kind in ("bullet", "bullet2", "number"):
            blocks.append(Block("bullet2", s[2:]))  # nested list item
        elif line.startswith((" ", "\t")) and not para and blocks and blocks[-1].kind in ("bullet", "bullet2", "number") \
                and lines[i - 1].strip():
            blocks[-1].text += " " + s  # continuation line of a list item
        elif s.startswith(">") and blocks and blocks[-1].kind == "quote" and lines[i - 1].strip().startswith(">"):
            blocks[-1].text += " " + s.lstrip("> ").strip()  # multi-line block quote
        elif re.match(r"[-*] ", s):
            flush()
            blocks.append(Block("bullet", s[2:]))
        elif re.match(r"\d+\. ", s) and not re.match(r"\d+\.\d", s):
            flush()
            blocks.append(Block("number", s))
        elif s.startswith(">"):
            flush()
            blocks.append(Block("quote", s.lstrip("> ").strip()))
        elif not s:
            flush()
        else:
            para.append(s)
        i += 1
    flush()
    return blocks


# =============================================================================================== DOCX helpers
def set_run_font(run, size: float = 14, bold: bool | None = None, italic: bool | None = None, mono: bool = False) -> None:
    run.font.name = "Courier New" if mono else FONT
    run.font.size = Pt(size)
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), run.font.name)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic


def add_inline(par, text: str, size: float = 14, bold: bool = False) -> None:
    """Inline Markdown: **bold**, `code`, [text](url) → text (url); \\* → *."""
    text = re.sub(r"\\([*_|#\[\]])", r"\1", text)
    # thousands separators → non-breaking spaces, so «1 528 887» never wraps inside the number
    text = re.sub(r"(?<=\d) (?=\d{3}(?!\d))", "\u00a0", text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1 (\2)", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)
    for part in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            set_run_font(par.add_run(part[2:-2]), size, bold=True)
        elif part.startswith("`") and part.endswith("`"):
            set_run_font(par.add_run(part[1:-1]), size - 2, mono=True)
        else:
            set_run_font(par.add_run(part), size, bold=bold or None)


def fmt_par(par, align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent: bool = True, spacing: float = 1.5,
            before: float = 0, after: float = 0, keep_next: bool = False) -> None:  # fmt: skip
    pf = par.paragraph_format
    pf.alignment = align
    pf.first_line_indent = Cm(1.25) if indent else Cm(0)
    pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE if spacing == 1.5 else WD_LINE_SPACING.SINGLE
    pf.space_before, pf.space_after = Pt(before), Pt(after)
    pf.keep_with_next = keep_next
    pf.widow_control = True


def add_field(par, instr: str) -> None:
    for kind, txt in (("begin", None), ("instr", instr), ("separate", None), ("text", "1"), ("end", None)):
        if kind == "instr":
            r = par.add_run()
            t = OxmlElement("w:instrText")
            t.set(qn("xml:space"), "preserve")
            t.text = txt
            r._element.append(t)
        elif kind == "text":
            set_run_font(par.add_run(txt), 12)
        else:
            r = par.add_run()
            fc = OxmlElement("w:fldChar")
            fc.set(qn("w:fldCharType"), kind)
            r._element.append(fc)


def fld_char(par, kind: str) -> None:
    r = par.add_run()
    fc = OxmlElement("w:fldChar")
    fc.set(qn("w:fldCharType"), kind)
    r._element.append(fc)


def set_cell_borders(table) -> None:
    tbl = table._tbl
    tblpr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:color"), "000000")
        borders.append(el)
    # CT_TblPr is an ordered sequence: tblBorders must precede shd/tblLayout/tblCellMar/tblLook.
    successor = next((tblpr.find(qn(f"w:{n}")) for n in ("shd", "tblLayout", "tblCellMar", "tblLook", "tblCaption")
                      if tblpr.find(qn(f"w:{n}")) is not None), None)  # fmt: skip
    if successor is not None:
        successor.addprevious(borders)
    else:
        tblpr.append(borders)


def heading_text(kind: str, text: str) -> str:
    """ГОСТ 7.32: no full stop after section numbers ('1 ОБЗОР', '1.1 Подраздел')."""
    return re.sub(r"^(\d+(?:\.\d+)*)\.\s", r"\1 ", text)


def is_wide_image(f: Path) -> bool:
    """Wide diagrams go on a landscape page (screenshots stay in portrait)."""
    if not f.exists() or "screenshots" in str(f):
        return False
    with Image.open(f) as im:
        w, h = im.size
    return w / h > 1.45


UNNUMBERED = ("АННОТАЦИЯ", "СОДЕРЖАНИЕ", "ВВЕДЕНИЕ", "ЗАКЛЮЧЕНИЕ", "СПИСОК", "ПРИЛОЖЕНИЕ")


# =============================================================================================== DOCX build
class NoteBuilder:
    def __init__(self, toc_pages: dict[str, int] | None) -> None:
        self.doc = Document()
        self.toc_pages = toc_pages
        self.fig = 0
        self.tab = 0
        self.formula = 0
        self.headings: list[tuple[int, str]] = []
        self.orientation = "P"
        self._landscape_used = False
        self._setup()

    def _setup(self) -> None:
        d = self.doc
        sec = d.sections[0]
        sec.page_width, sec.page_height = Mm(210), Mm(297)
        sec.left_margin, sec.right_margin = Mm(30), Mm(15)
        sec.top_margin, sec.bottom_margin = Mm(20), Mm(20)
        sec.footer_distance = Mm(10)
        sec.different_first_page_header_footer = True  # title page without a number (ГОСТ 7.32)
        fp = sec.footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        add_field(fp, "PAGE")
        normal = d.styles["Normal"]
        normal.font.name, normal.font.size = FONT, Pt(14)
        normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        for name, size in (("Heading 1", 14), ("Heading 2", 14), ("Heading 3", 14)):
            st = d.styles[name]
            st.font.name, st.font.size, st.font.bold = FONT, Pt(size), True
            st.font.color.rgb = RGBColor(0, 0, 0)
            st.font.italic = False
            rpr = st.element.get_or_add_rPr()
            rf = rpr.find(qn("w:rFonts"))
            if rf is None:
                rf = OxmlElement("w:rFonts")
                rpr.insert(0, rf)
            for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
                rf.set(qn(a), FONT)
            for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
                if rf.get(qn(a)) is not None:
                    del rf.attrib[qn(a)]
            pf = st.paragraph_format
            pf.space_before, pf.space_after = Pt(12 if name == "Heading 1" else 12), Pt(12)
            pf.keep_with_next = True
            pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        # Ask Word to refresh fields (TOC, PAGE) when the document is opened.
        settings = d.settings.element
        upd = OxmlElement("w:updateFields")
        upd.set(qn("w:val"), "true")
        # CT_Settings is ordered too: updateFields comes right before hdrShapeDefaults / footnotePr / ...
        later = ("hdrShapeDefaults", "footnotePr", "endnotePr", "compat", "docVars", "rsids", "mathPr",
                 "attachedSchema", "themeFontLang", "clrSchemeMapping", "doNotIncludeSubdocsInStats",
                 "doNotAutoCompressPictures", "forceUpgrade", "captions", "readModeInkLockDown", "smartTagType",
                 "schemaLibrary", "shapeDefaults", "doNotEmbedSmartTags", "decimalSymbol", "listSeparator")  # fmt: skip
        successor = next((settings.find(qn(f"w:{n}")) for n in later if settings.find(qn(f"w:{n}")) is not None), None)
        if successor is not None:
            successor.addprevious(upd)
        else:
            settings.append(upd)
        zoom = settings.find(qn("w:zoom"))
        if zoom is not None and zoom.get(qn("w:percent")) is None:
            zoom.set(qn("w:percent"), "100")  # required attribute missing in python-docx's template

    # ------------------------------------------------------------------ elements
    def title_page(self, lines: list[str]) -> None:
        blocks: list[list[str]] = [[]]
        for ln in lines:
            if ln.strip():
                blocks[-1].append(ln.strip())
            elif blocks[-1]:
                blocks.append([])
        # layout: header (2 lines) / course / big title / topic / authors / teachers / city-year
        spacer = {1: 70, 2: 40, 3: 10, 4: 60, 5: 20, 6: 90}
        for n, group in enumerate(b for b in blocks if b):
            for k, ln in enumerate(group):
                p = self.doc.add_paragraph()
                big = ln == "ПОЯСНИТЕЛЬНАЯ ЗАПИСКА"
                topic = n == 3
                right = n in (4, 5)
                fmt_par(p, align=WD_ALIGN_PARAGRAPH.RIGHT if right else WD_ALIGN_PARAGRAPH.CENTER, indent=False,
                        spacing=1.0 if not topic else 1.5, before=spacer.get(n, 0) if k == 0 else 0)  # fmt: skip
                add_inline(p, ln, 16 if big else 14, bold=big or topic)
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def heading(self, kind: str, text: str) -> None:
        text = heading_text(kind, text)
        level = {"h1": 1, "h2": 2, "h3": 3}[kind]
        last = self.doc.paragraphs[-1] if self.doc.paragraphs else None
        starts_section = last is not None and last._p.find(qn("w:pPr")) is not None and \
            last._p.pPr.find(qn("w:sectPr")) is not None
        if level == 1 and last is not None and last.text != "" and not starts_section:
            last.add_run().add_break(WD_BREAK.PAGE)
        if level == 1 and text.startswith("СОДЕРЖАНИЕ"):
            p = self.doc.add_paragraph()  # not a Heading: the TOC must not list itself
            fmt_par(p, WD_ALIGN_PARAGRAPH.CENTER, indent=False, after=12)
            add_inline(p, text, 14, bold=True)
            return
        if level == 1 and text.startswith("ПРИЛОЖЕНИЕ"):
            m = re.match(r"(ПРИЛОЖЕНИЕ\s+\S+)\.\s*(.*)", text)
            label, title = (m.group(1), m.group(2)) if m else (text, "")
            p = self.doc.add_paragraph(style="Heading 1")
            fmt_par(p, WD_ALIGN_PARAGRAPH.CENTER, indent=False, keep_next=True)
            set_run_font(p.add_run(label), 14, bold=True)
            if title:
                p.add_run().add_break()
                set_run_font(p.add_run(title), 14, bold=True)
            self.headings.append((1, f"{label}. {title}" if title else label))
            return
        p = self.doc.add_paragraph(style=f"Heading {level}")
        centered = level == 1 and text.startswith(UNNUMBERED)
        fmt_par(p, WD_ALIGN_PARAGRAPH.CENTER if centered else WD_ALIGN_PARAGRAPH.LEFT, indent=not centered,
                before=12, after=12, keep_next=True)  # fmt: skip
        add_inline(p, text, 14, bold=True)
        if level <= 2 and not text.startswith("АННОТАЦИЯ"):
            self.headings.append((level, text))

    def toc(self) -> None:
        entries = self.toc_pages or {}
        p = None
        items = self._toc_items
        for idx, (level, text) in enumerate(items):
            p = self.doc.add_paragraph()
            fmt_par(p, WD_ALIGN_PARAGRAPH.LEFT, indent=False, spacing=1.5)
            p.paragraph_format.left_indent = Cm(0 if level == 1 else 0.75)
            p.paragraph_format.tab_stops.add_tab_stop(Mm(TEXT_W_MM), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
            if idx == 0:
                fld_char(p, "begin")
                r = p.add_run()
                t = OxmlElement("w:instrText")
                t.set(qn("xml:space"), "preserve")
                t.text = 'TOC \\o "1-2" \\h \\z \\u'
                r._element.append(t)
                fld_char(p, "separate")
            page = entries.get(text, 0)
            add_inline(p, f"{text}\t{page if page else '00'}", 14)
        if p is not None:
            fld_char(p, "end")

    def paragraph(self, text: str) -> None:
        p = self.doc.add_paragraph()
        fmt_par(p)
        add_inline(p, text)

    def bullet(self, text: str, level: int = 1) -> None:
        p = self.doc.add_paragraph()
        fmt_par(p)
        if level == 2:
            p.paragraph_format.left_indent = Cm(1.0)
        add_inline(p, ("– " if level == 1 else "• ") + text)

    def numbered(self, text: str, in_biblio: bool) -> None:
        p = self.doc.add_paragraph()
        fmt_par(p, indent=not in_biblio)
        if in_biblio:  # hanging layout for the reference list
            p.paragraph_format.left_indent = Cm(0)
            p.paragraph_format.first_line_indent = Cm(1.25)
        add_inline(p, text)

    def quote(self, text: str) -> None:
        p = self.doc.add_paragraph()
        fmt_par(p)
        p.paragraph_format.left_indent = Cm(1.0)
        add_inline(p, text, 13)

    def table(self, rows: list[list[str]], caption: str | None) -> None:
        if not rows:
            return
        ncols = max(len(r) for r in rows)
        wide = ncols > 9  # orientation is handled by the build loop (_orient)
        if caption:
            if caption.startswith("!"):
                label = caption[1:]
            else:
                self.tab += 1
                label = f"Таблица {self.tab} — {caption}"
            cp = self.doc.add_paragraph()
            fmt_par(cp, WD_ALIGN_PARAGRAPH.LEFT, indent=False, before=6, keep_next=True)
            add_inline(cp, label, 14)
        size = 12 if ncols <= 5 else 10 if ncols <= 9 else 8
        t = self.doc.add_table(rows=len(rows), cols=ncols)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        set_cell_borders(t)
        # Column widths: every column gets at least the width of its longest word at this
        # font size (so «NFR-01» never wraps letter by letter); the remaining width is
        # shared in proportion to the amount of text in the column.
        avail_mm = (297 - 20 - 15) if wide else TEXT_W_MM
        char_mm = size * 0.21  # average Times New Roman glyph ≈ 0.6 em; 1 pt = 0.353 mm
        mins, weights = [], []
        for ci in range(ncols):
            col = [r[ci] if ci < len(r) else "" for r in rows]
            # numbers with thousands separators count as ONE word (they never wrap, see add_inline)
            col_nb = [re.sub(r"(?<=\d) (?=\d{3}(?!\d))", "\u00a0", c) for c in col]
            longest_word = max((len(w) for c in col_nb for w in c.split(" ") if w), default=1)
            mins.append(min(longest_word + 1, 16) * char_mm + 3.0)  # +1: bold header glyphs are wider
            weights.append(min(max(len(c) for c in col), 60) + 1)
        spare = avail_mm - sum(mins)
        if spare < 0:  # too many columns: scale the minima down
            mins = [m * avail_mm / sum(mins) for m in mins]
            spare = 0
        widths = [Mm(m + spare * w / sum(weights)) for m, w in zip(mins, weights, strict=True)]
        for ci, w_ in enumerate(widths):
            t.columns[ci].width = w_  # writes <w:gridCol>, which LibreOffice and Word use for layout
        for ri, row in enumerate(rows):
            for ci in range(ncols):
                cell = t.cell(ri, ci)
                cell.width = widths[ci]
                txt = row[ci] if ci < len(row) else ""
                par = cell.paragraphs[0]
                fmt_par(par, WD_ALIGN_PARAGRAPH.LEFT, indent=False, spacing=1.0)
                add_inline(par, txt.replace("<br>", " "), size, bold=ri == 0)
            trpr_ = t.rows[ri]._tr.get_or_add_trPr()
            cs = OxmlElement("w:cantSplit")  # a row never breaks across pages
            cs.set(qn("w:val"), "true")
            trpr_.append(cs)
            if ri == 0:  # repeat the header row on every page
                trpr = t.rows[0]._tr.get_or_add_trPr()
                h = OxmlElement("w:tblHeader")
                h.set(qn("w:val"), "true")
                trpr.append(h)
        after = self.doc.add_paragraph()
        fmt_par(after, indent=False, spacing=1.0)

    def _orient(self, target: str, new_item: bool) -> None:
        """Switch page orientation lazily: a new section only when the orientation
        changes, a page break between two landscape items, never an empty page."""
        if target == self.orientation:
            if target == "L" and new_item and self._landscape_used:
                self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
                self._landscape_used = False
            return
        self._landscape(target == "L")
        self.orientation = target
        self._landscape_used = False

    def _landscape(self, on: bool) -> None:
        sec = self.doc.add_section(WD_SECTION.NEW_PAGE)
        sec.orientation = WD_ORIENT.LANDSCAPE if on else WD_ORIENT.PORTRAIT
        w, h = (Mm(297), Mm(210)) if on else (Mm(210), Mm(297))
        sec.page_width, sec.page_height = w, h
        sec.left_margin, sec.right_margin = Mm(30 if not on else 20), Mm(15)
        sec.top_margin, sec.bottom_margin = Mm(20), Mm(20)
        sec.different_first_page_header_footer = False
        sec.footer.is_linked_to_previous = True

    def image(self, path: str, caption: str | None, landscape_open: bool = False) -> None:
        f = Path(path)
        if not f.exists():
            self.paragraph(f"[ЗАПОЛНИТЬ: отсутствует рисунок {f.name}]")
            return
        with Image.open(f) as im:
            w, h = im.size
        # Wide diagrams (component, deployment, ER, sequence...) are unreadable at portrait
        # text width: they get their own landscape page (allowed by ГОСТ 7.32).
        wide = is_wide_image(f)  # orientation is handled by the build loop (_orient)
        max_w, max_h = (Mm(297 - 20 - 15), Mm(150)) if wide else (Mm(TEXT_W_MM), Mm(195))
        width = max_w
        if Emu(int(width * h / w)) > max_h:
            width = Emu(int(max_h * w / h))
        p = self.doc.add_paragraph()
        fmt_par(p, WD_ALIGN_PARAGRAPH.CENTER, indent=False, spacing=1.0, before=6, keep_next=True)
        p.add_run().add_picture(str(f), width=width)
        self.fig += 1
        cp = self.doc.add_paragraph()
        fmt_par(cp, WD_ALIGN_PARAGRAPH.CENTER, indent=False, after=6)
        caption = re.sub(r"^Рисунок\s+\d+\s+—\s+", "", caption or "")
        add_inline(cp, f"Рисунок {self.fig} — {caption}", 14)

    def formulas(self, lines: list[str]) -> None:
        for ln in lines:
            self.formula += 1
            p = self.doc.add_paragraph()
            fmt_par(p, WD_ALIGN_PARAGRAPH.LEFT, indent=False, before=3, after=3)
            ts = p.paragraph_format.tab_stops
            ts.add_tab_stop(Mm(TEXT_W_MM / 2), WD_TAB_ALIGNMENT.CENTER)
            ts.add_tab_stop(Mm(TEXT_W_MM), WD_TAB_ALIGNMENT.RIGHT)
            size = 13 if len(ln) < 70 else 11
            set_run_font(p.add_run(f"\t{ln.strip()}\t({self.formula})"), size, italic=False)

    def code(self, lines: list[str]) -> None:
        for ln in lines:
            p = self.doc.add_paragraph()
            fmt_par(p, WD_ALIGN_PARAGRAPH.LEFT, indent=False, spacing=1.0)
            p.paragraph_format.left_indent = Cm(0.5)
            set_run_font(p.add_run(ln), 10, mono=True)
        self.doc.add_paragraph()

    # ------------------------------------------------------------------ driver
    def build(self, blocks: list[Block]) -> Document:
        # first pass over headings to know the TOC items (same list in both passes)
        self._toc_items = []
        for b in blocks:
            if b.kind in ("h1", "h2"):
                t = heading_text(b.kind, b.text)
                if t.startswith(("АННОТАЦИЯ", "СОДЕРЖАНИЕ")):
                    continue
                if b.kind == "h1" and t.startswith("ПРИЛОЖЕНИЕ"):
                    m = re.match(r"(ПРИЛОЖЕНИЕ\s+\S+)\.\s*(.*)", t)
                    t = f"{m.group(1)}. {m.group(2)}" if m else t
                self._toc_items.append((1 if b.kind == "h1" else 2, t))
        in_biblio = False
        landscape_open = False
        for idx, b in enumerate(blocks):
            nxt = blocks[idx + 1] if idx + 1 < len(blocks) else None
            heading_of_wide = (b.kind in ("h2", "h3") and nxt is not None and nxt.kind == "image"
                               and is_wide_image(Path(nxt.text)))  # fmt: skip
            wide_item = (b.kind == "image" and is_wide_image(Path(b.text))) or (
                b.kind == "table" and max((len(r) for r in b.rows), default=0) > 9)
            if b.kind != "title":
                if heading_of_wide or wide_item:
                    # an image right after its own heading stays on the heading's page
                    self._orient("L", new_item=not landscape_open)
                    landscape_open = heading_of_wide
                else:
                    self._orient("P", new_item=False)
            if b.kind == "title":
                self.title_page(b.lines)
            elif b.kind in ("h1", "h2", "h3"):
                in_biblio = b.kind == "h1" and b.text.startswith("СПИСОК")
                self.heading(b.kind, b.text)
            elif b.kind == "toc":
                self.toc()
            elif b.kind == "p":
                self.paragraph(b.text)
            elif b.kind == "bullet":
                self.bullet(b.text)
            elif b.kind == "bullet2":
                self.bullet(b.text, level=2)
            elif b.kind == "number":
                self.numbered(b.text, in_biblio)
            elif b.kind == "quote":
                self.quote(b.text)
            elif b.kind == "table":
                self.table(b.rows, b.caption)
            elif b.kind == "image":
                self.image(b.text, b.caption)
            elif b.kind == "formula":
                self.formulas(b.lines)
            elif b.kind == "code":
                self.code(b.lines)
            if self.orientation == "L" and b.kind in ("image", "table"):
                self._landscape_used = True
        return self.doc


def save_docx(doc: Document, path: Path) -> None:
    doc.save(path)
    # Drop directory entries from the ZIP (Word refuses some files that contain them).
    tmp = path.with_suffix(".tmp")
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if not item.filename.endswith("/"):
                zout.writestr(item, zin.read(item.filename))
    tmp.replace(path)


def to_pdf(path: Path, outdir: Path) -> Path:
    outdir.mkdir(exist_ok=True)
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(outdir), str(path)],
                   check=True, capture_output=True, timeout=600)  # fmt: skip
    return outdir / (path.stem + ".pdf")


def pdf_pages(pdf: Path) -> list[str]:
    txt = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], check=True, capture_output=True, text=True).stdout
    return txt.split("\f")


def norm(s: str) -> str:
    """Whitespace- and punctuation-insensitive form, robust to line wrapping in the PDF."""
    return re.sub(r"[\s.,:;«»\"'()–—-]+", "", s).lower()


def find_heading_pages(pdf: Path, items: list[tuple[int, str]]) -> dict[str, int]:
    pages = [norm(p) for p in pdf_pages(pdf)]
    # The TOC itself contains every heading: start searching after the page where the
    # last TOC entry first appears.
    last_key = norm(items[-1][1])[:40]
    toc_end = next(i for i, p in enumerate(pages) if last_key in p)
    found: dict[str, int] = {}
    start = toc_end + 1
    for _, text in items:
        key = norm(text)[:40]
        for i in range(start, len(pages)):
            if key in pages[i]:
                found[text] = i + 1  # physical page number = displayed number (title page counted)
                start = i
                break
    return found


def build_docx(make_pdf: bool) -> tuple[Path, Path | None]:
    blocks = parse(read_md(NOTE_MD))
    if not make_pdf:
        b = NoteBuilder(None)
        save_docx(b.build(blocks), DOCX_OUT)
        return DOCX_OUT, None
    b1 = NoteBuilder(None)
    save_docx(b1.build(blocks), DOCX_OUT)
    pdf1 = to_pdf(DOCX_OUT, REVIEW)
    pages = find_heading_pages(pdf1, b1._toc_items)
    missing = [t for _, t in b1._toc_items if t not in pages]
    if missing:
        print("WARNING: headings not located in PDF:", missing, file=sys.stderr)
    b2 = NoteBuilder(pages)
    save_docx(b2.build(blocks), DOCX_OUT)
    pdf2 = to_pdf(DOCX_OUT, REVIEW)
    check = find_heading_pages(pdf2, b2._toc_items)
    drift = {t: (pages[t], check.get(t)) for t in pages if check.get(t) != pages[t]}
    if drift:
        print("WARNING: TOC page drift after pass 2:", drift, file=sys.stderr)
    return DOCX_OUT, pdf2


# =============================================================================================== PPTX
NAVY, ICE, AMBER, INK, MUTED, WHITE = "14324A", "E8F1F8", "F2A541", "1B1B1B", "5B6670", "FFFFFF"


def rgb(h: str):  # noqa: ANN201 - python-pptx has its own RGBColor class
    from pptx.dml.color import RGBColor as PptxRGB

    return PptxRGB.from_string(h)


def parse_slides(path: Path) -> list[dict]:
    text = re.sub(r"<!--.*?-->", "", path.read_text(encoding="utf-8"), flags=re.S)
    slides = []
    for chunk in re.split(r"^## ", text, flags=re.M)[1:]:
        lines = chunk.strip().splitlines()
        m = re.match(r"Слайд (\d+)\. (.+)", lines[0])
        s = {"n": int(m.group(1)), "title": m.group(2).strip(), "bullets": [], "image": None, "notes": ""}
        for ln in lines[1:]:
            if ln.startswith("- "):
                s["bullets"].append(ln[2:].strip())
            elif ln.startswith("Изображение:"):
                s["image"] = (HERE / ln.split(":", 1)[1].strip()).resolve()
            elif ln.startswith("Заметки:"):
                s["notes"] = ln.split(":", 1)[1].strip()
        slides.append(s)
    return slides


def build_pptx() -> Path:
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
    from pptx.util import Inches
    from pptx.util import Pt as PPt

    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]
    slides = parse_slides(SLIDES_MD)
    total = len(slides)

    def text_box(slide, x, y, w, h, paras, size, color, bold=False, font="Calibri", align=PP_ALIGN.LEFT,
                 anchor=MSO_ANCHOR.TOP, space_after=8):  # fmt: skip
        tb = slide.shapes.add_textbox(x, y, w, h)
        tf = tb.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = anchor
        tf.margin_left = tf.margin_right = 0
        for i, ptxt in enumerate(paras):
            par = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            par.alignment = align
            par.space_after = PPt(space_after)
            run = par.add_run()
            run.text = ptxt
            run.font.size, run.font.bold, run.font.name = PPt(size), bold, font
            run.font.color.rgb = rgb(color)
        return tb

    def badge(slide, n, dark: bool) -> None:
        """Motif: slide number in an amber circle (top-left), repeated on every slide."""
        c = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(0.6), Inches(0.52), Inches(0.62), Inches(0.62))
        c.fill.solid()
        c.fill.fore_color.rgb = rgb(AMBER)
        c.line.fill.background()
        tf = c.text_frame
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = str(n)
        r.font.size, r.font.bold, r.font.name = PPt(16), True, "Calibri"
        r.font.color.rgb = rgb(NAVY)
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE

    def footer(slide, dark: bool) -> None:
        text_box(slide, Inches(0.6), Inches(7.0), Inches(9), Inches(0.3),
                 ["AccessAstana · ASDP · Astana IT University, 2026"], 10, ICE if dark else MUTED)  # fmt: skip
        text_box(slide, Inches(11.9), Inches(7.0), Inches(0.83), Inches(0.3), [f"{_n}/{total}"], 10,
                 ICE if dark else MUTED, align=PP_ALIGN.RIGHT)  # fmt: skip

    def add_picture_fit(slide, path: Path, x, y, w, h) -> None:
        with Image.open(path) as im:
            iw, ih = im.size
        scale = min(w / iw, h / ih)
        pw, ph = int(iw * scale), int(ih * scale)
        pic = slide.shapes.add_picture(str(path), x + (w - pw) // 2, y + (h - ph) // 2, pw, ph)
        pic.line.color.rgb = rgb("D5DEE6")
        pic.line.width = PPt(0.75)

    for s in slides:
        _n = s["n"]
        slide = prs.slides.add_slide(blank)
        dark = _n in (1, total)
        bg = slide.background.fill
        bg.solid()
        bg.fore_color.rgb = rgb(NAVY if dark else WHITE)
        badge(slide, _n, dark)
        title_color = WHITE if dark else NAVY
        if _n == 1:  # title slide
            text_box(slide, Inches(0.6), Inches(1.5), Inches(6.6), Inches(2.6), [s["title"]], 34, title_color,
                     bold=True, font="Cambria")  # fmt: skip
            text_box(slide, Inches(0.6), Inches(4.3), Inches(6.4), Inches(2.0), s["bullets"], 16, ICE)
            if s["image"] and s["image"].exists():
                add_picture_fit(slide, s["image"], Inches(7.5), Inches(0.9), Inches(5.3), Inches(5.7))
        else:
            text_box(slide, Inches(1.45), Inches(0.45), Inches(11.3), Inches(0.9), [s["title"]], 30, title_color,
                     bold=True, font="Cambria", anchor=MSO_ANCHOR.MIDDLE)  # fmt: skip
            body_color = WHITE if dark else INK
            if s["image"] and s["image"].exists():
                text_box(slide, Inches(0.6), Inches(1.65), Inches(5.2), Inches(5.0), ["• " + b for b in s["bullets"]],
                         17, body_color, space_after=12)  # fmt: skip
                add_picture_fit(slide, s["image"], Inches(6.1), Inches(1.55), Inches(6.65), Inches(5.2))
            else:  # card grid for slides without an image
                n = len(s["bullets"])
                cols = 2 if n > 3 else 1
                rows_ = (n + cols - 1) // cols
                gw, gh, gap = Inches(12.13), Inches(5.0), Inches(0.3)
                cw = (gw - gap * (cols - 1)) // cols
                ch = (gh - gap * (rows_ - 1)) // rows_
                for i, btxt in enumerate(s["bullets"]):
                    r_, c_ = divmod(i, cols)
                    x = Inches(0.6) + (cw + gap) * c_
                    y = Inches(1.65) + (ch + gap) * r_
                    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, cw, ch)
                    card.adjustments[0] = 0.08
                    card.fill.solid()
                    card.fill.fore_color.rgb = rgb(ICE if not dark else "1F4566")
                    card.line.fill.background()
                    text_box(slide, x + Inches(0.3), y, cw - Inches(0.6), ch, [btxt], 18, body_color,
                             anchor=MSO_ANCHOR.MIDDLE)  # fmt: skip
        footer(slide, dark)
        slide.notes_slide.notes_text_frame.text = s["notes"]
    prs.save(PPTX_OUT)
    return PPTX_OUT


# =============================================================================================== placeholders
def report_placeholders(docx_pdf: Path | None, pptx_pdf: Path | None) -> str:
    lines = ["Оставшиеся пометки [ЗАПОЛНИТЬ] / [НУЖЕН ИСТОЧНИК]:"]
    for label, pdf in (("Пояснительная записка", docx_pdf), ("Презентация", pptx_pdf)):
        if pdf is None:
            continue
        for i, page in enumerate(pdf_pages(pdf), start=1):
            flat = re.sub(r"\s+", " ", page)
            for m in PLACEHOLDER_RE.finditer(flat):
                lines.append(f"  {label}, {'стр.' if 'записка' in label else 'слайд'} {i}: {m.group(0)}")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-pdf", action="store_true")
    args = ap.parse_args()
    subprocess.run([sys.executable, str(HERE / "budget" / "budget_model.py")], check=True)
    docx_path, docx_pdf = build_docx(not args.no_pdf)
    pptx_path = build_pptx()
    pptx_pdf = None if args.no_pdf else to_pdf(pptx_path, REVIEW)
    print("wrote", docx_path, "and", pptx_path)
    if not args.no_pdf:
        report = report_placeholders(docx_pdf, pptx_pdf)
        (REVIEW / "placeholders.txt").write_text(report, encoding="utf-8")
        print(report)
    shutil.rmtree(HERE / "__pycache__", ignore_errors=True)


if __name__ == "__main__":
    main()
