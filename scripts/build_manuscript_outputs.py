"""Build offline HTML MathML and editable Word equations from the manuscript.

Install scripts/requirements-documents.txt before running. Isolated packages in
scripts/_math_deps are supported but not committed. Pandoc exports native OMML.
"""
from __future__ import annotations

import html
import json
import re
import sys
import tempfile
import zipfile
from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "manuscript_en.md"
OUT_HTML = ROOT / "manuscript_en.html"
OUT_DOCX = ROOT / "manuscript_en.docx"
LOCAL_DEPS = Path(__file__).resolve().parent / "_math_deps"
if LOCAL_DEPS.is_dir():
    sys.path.insert(0, str(LOCAL_DEPS))

from latex2mathml.converter import convert as latex_to_mathml
import pypandoc

INLINE_TOKEN = re.compile(r"(`[^`\n]+`|\$(?!\$)(?:\\.|[^$\n])+\$)")


def equation_parts(latex: str) -> tuple[str, str | None]:
    tag = re.search(r"\\tag\{(\d+)\}", latex)
    return re.sub(r"\\tag\{\d+\}", "", latex).strip(), tag.group(1) if tag else None


@lru_cache(maxsize=128)
def math_markup(latex: str, display: bool = False) -> str:
    # Normalize a standard operator alias accepted by TeX but not this converter.
    latex = re.sub(r"\\arg(?![A-Za-z])", r"\\operatorname{arg}", latex)
    result = latex_to_mathml(latex, display="block" if display else "inline")
    visible = "".join(ET.fromstring(result).itertext())
    if re.search(r"\\[A-Za-z]+", visible):
        raise ValueError("Unconverted LaTeX command: " + latex)
    return result


def plain_inline_html(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"\[([^]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    return re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)


def inline_html(text: str) -> str:
    parts = []
    for token in INLINE_TOKEN.split(text):
        if token.startswith("`") and token.endswith("`"):
            parts.append("<code>" + html.escape(token[1:-1]) + "</code>")
        elif token.startswith("$") and token.endswith("$"):
            parts.append(math_markup(token[1:-1]))
        else:
            parts.append(plain_inline_html(token))
    return "".join(parts)


def parse_table(lines: list[str], start: int):
    header = [c.strip() for c in lines[start].strip().strip("|").split("|")]
    rows = []
    i = start + 2
    while i < len(lines) and lines[i].strip().startswith("|"):
        rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
        i += 1
    return header, rows, i


def read_equation(lines: list[str], start: int) -> tuple[str, int]:
    content = []
    i = start + 1
    while i < len(lines) and lines[i].strip() != "$$":
        content.append(lines[i])
        i += 1
    if i == len(lines):
        raise ValueError(f"Unclosed display equation at line {start + 1}")
    return "\n".join(content).strip(), i + 1


def markdown_to_html(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    paragraph: list[str] = []
    i = 0

    def flush():
        if paragraph:
            out.append("<p>" + inline_html(" ".join(paragraph)) + "</p>")
            paragraph.clear()

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            flush()
            i += 1
        elif match := re.match(r"^(#{1,3}) (.*)", line):
            flush()
            level = len(match.group(1))
            out.append(f"<h{level}>{inline_html(match.group(2))}</h{level}>")
            i += 1
        elif line.startswith("!["):
            flush()
            match = re.fullmatch(r"!\[([^]]*)\]\(([^)]+)\)", line)
            if not match:
                raise ValueError("Malformed figure: " + line)
            alt, src = match.groups()
            out.append(f'<figure><img src="{html.escape(src, quote=True)}" alt="{html.escape(alt, quote=True)}"></figure>')
            i += 1
        elif line.startswith(("**Figure", "**Table")):
            flush()
            out.append(f'<p class="caption">{inline_html(line)}</p>')
            i += 1
        elif line.strip() == "$$":
            flush()
            latex, i = read_equation(lines, i)
            expression, number = equation_parts(latex)
            label = f'<span class="equation-number">({number})</span>' if number else ""
            out.append('<div class="equation">' + math_markup(expression, True) + label + '</div>')
        elif line.startswith("|") and i + 1 < len(lines) and lines[i + 1].startswith("|"):
            flush()
            header, rows, i = parse_table(lines, i)
            out.append('<div class="table-scroll"><table><thead><tr>' + "".join(f"<th>{inline_html(c)}</th>" for c in header) + "</tr></thead><tbody>")
            for row in rows:
                out.append("<tr>" + "".join(f"<td>{inline_html(c)}</td>" for c in row) + "</tr>")
            out.append("</tbody></table></div>")
        elif line.startswith("-"):
            flush()
            items = []
            while i < len(lines) and lines[i].startswith("-"):
                items.append("<li>" + inline_html(lines[i][1:].strip()) + "</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
        else:
            paragraph.append(line.strip())
            i += 1
    flush()
    return "\n".join(out)


def main():
    from docx import Document
    from docx.shared import Inches, Pt

    text = MD.read_text(encoding="utf-8")
    body = markdown_to_html(text)
    style = """
    body{font-family:Georgia,'Times New Roman',serif;max-width:1100px;margin:40px auto;padding:0 24px;line-height:1.65;color:#202124}
    h1{text-align:center;font-size:2em;line-height:1.2;margin-bottom:1.4em} h2{margin-top:2em;border-bottom:1px solid #bbb;padding-bottom:.2em} h3{margin-top:1.4em}
    table{border-collapse:collapse;width:100%;margin:1em 0;font-size:.92em} th,td{border:1px solid #aaa;padding:6px 8px;vertical-align:top} th{background:#f1f3f4} .table-scroll{overflow-x:auto}
    figure{text-align:center;margin:1.3em 0} figure img{max-width:100%;height:auto} .caption{font-size:.9em;color:#4b5563}
    .equation{display:flex;align-items:center;gap:16px;overflow-x:auto;padding:14px 0;margin:1em 0;}
    .equation math{flex:1;min-width:max-content;} .equation-number{flex:none;margin-left:auto;}
    math{font-family:'Cambria Math','STIX Two Math',math;} code{font-family:Consolas,monospace;overflow-wrap:anywhere}
    @media(max-width:600px){body{padding:0 12px;margin:20px auto}h1{font-size:1.4em}.equation{font-size:.9em}}
    @media print{body{margin:0;max-width:none;padding:0;font-size:10pt}.equation,.table-scroll{overflow:visible}figure{break-inside:avoid}}
    """
    page = "<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>Low-Label Output Calibration</title><style>" + style + "</style></head><body>" + body + "</body></html>"
    reference_doc = Document()
    sec = reference_doc.sections[0]
    sec.page_width = Inches(8.5)
    sec.page_height = Inches(11)
    sec.top_margin = sec.bottom_margin = Inches(.7)
    sec.left_margin = sec.right_margin = Inches(.7)
    normal = reference_doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(10.5)
    for name in ["Heading 1", "Heading 2", "Heading 3"]:
        reference_doc.styles[name].font.name = "Times New Roman"
    # Pandoc's texmath writer handles fractions, accents and limits as native OMML.
    # Its math reader ignores tag, so include the unchanged number as math text.
    word_text = re.sub(r"\\tag\{(\d+)\}", lambda m: r"\qquad\text{(" + m.group(1) + ")}", text)
    with tempfile.TemporaryDirectory(prefix="manuscript-word-") as temp:
        reference = Path(temp) / "reference.docx"
        generated = Path(temp) / "manuscript.docx"
        reference_doc.save(reference)
        pypandoc.convert_text(word_text, to="docx", format="markdown+tex_math_dollars",
            outputfile=str(generated), extra_args=["--standalone",
            "--reference-doc=" + str(reference), "--resource-path=" + str(ROOT)])
        with zipfile.ZipFile(generated) as archive:
            content = archive.read("word/document.xml")
        if content.count(b"<m:oMathPara>") != 10:
            raise ValueError("Expected 10 Word display equations")
        # Replace outputs only after both conversion paths complete successfully.
        OUT_HTML.write_text(page, encoding="utf-8")
        OUT_DOCX.write_bytes(generated.read_bytes())
    print(json.dumps({"html": str(OUT_HTML), "docx": str(OUT_DOCX),
        "markdown_lines": len(text.splitlines()),
        "html_math_objects": len(re.findall(r"<math\b", page)),
        "display_equations": len(re.findall(r"^\$\$\s*$", text, re.M)) // 2,
        "html_math_backend": "offline native MathML",
        "word_math_backend": "editable Office Math (OMML)"}, indent=2))


if __name__ == "__main__":
    main()
