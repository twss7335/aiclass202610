"""Publish existing result files and papers to docs/ without training or plotting."""

from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
PAPERS = ROOT / "paper"
DOCS = ROOT / "docs"
REPORTS = DOCS / "reports"
FIGURES = DOCS / "figures"
ARTIFACTS = DOCS / "artifacts"

METRIC_SOURCES = {
    "iris": "results/metrics.json",
    "ai4i": "results/ai4i/metrics.json",
}
PAPER_SOURCES = {
    "iris_study": "paper/iris_study.md",
    "ai4i_study": "paper/ai4i_study.md",
}


def local_url(url: str) -> str:
    """Rewrite report-relative source links to copied static assets."""
    if url.startswith("../results/"):
        relative = Path(url.removeprefix("../results/"))
        source = RESULTS / relative
        if not source.is_file():
            raise FileNotFoundError(source)
        if source.suffix.lower() == ".png":
            return "../figures/" + relative.as_posix()
        target = ARTIFACTS / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        return "../artifacts/" + relative.as_posix()
    if url.startswith("../data/"):
        return "https://github.com/twss7335/aiclass202610/tree/main/" + url.removeprefix("../")
    if url.startswith("https://") or url.startswith("http://"):
        return url
    raise ValueError(f"Unexpected report link: {url}")


INLINE = re.compile(r"(!?)\[([^\]]+)\]\(([^)]+)\)|`([^`]+)`|\*([^*]+)\*")


def inline(source: str) -> str:
    """Render the small Markdown subset used in the two existing papers."""
    output = []
    position = 0
    for match in INLINE.finditer(source):
        output.append(html.escape(source[position:match.start()]))
        if match.group(2) is not None:
            label = html.escape(match.group(2))
            url = html.escape(local_url(match.group(3)), quote=True)
            if match.group(1):
                output.append(f'<figure><img src="{url}" alt="{label}" loading="lazy"><figcaption>{label}</figcaption></figure>')
            else:
                output.append(f'<a href="{url}">{label}</a>')
        elif match.group(4) is not None:
            output.append(f"<code>{html.escape(match.group(4))}</code>")
        else:
            output.append(f"<em>{html.escape(match.group(5))}</em>")
        position = match.end()
    output.append(html.escape(source[position:]))
    return "".join(output)


def is_separator(line: str) -> bool:
    return bool(re.fullmatch(r"\|[\s:|\-]+\|", line)) and "-" in line


def table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def render_markdown(source: str) -> str:
    lines = source.splitlines()
    output = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            level = len(heading.group(1))
            output.append(f"<h{level}>{inline(heading.group(2))}</h{level}>")
            index += 1
            continue
        if line.startswith("|") and index + 1 < len(lines) and is_separator(lines[index + 1].strip()):
            headings = table_cells(line)
            output.append("<div class=\"table-wrap\"><table><thead><tr>" +
                          "".join(f"<th>{inline(cell)}</th>" for cell in headings) +
                          "</tr></thead><tbody>")
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                cells = table_cells(lines[index])
                if len(cells) != len(headings):
                    raise ValueError("Report table has inconsistent column counts")
                output.append("<tr>" + "".join(f"<td>{inline(cell)}</td>" for cell in cells) + "</tr>")
                index += 1
            output.append("</tbody></table></div>")
            continue
        if re.match(r"^\d+\.\s", line):
            output.append("<ol>")
            while index < len(lines) and re.match(r"^\d+\.\s", lines[index].strip()):
                item = re.sub(r"^\d+\.\s+", "", lines[index].strip())
                output.append(f"<li>{inline(item)}</li>")
                index += 1
            output.append("</ol>")
            continue
        if line.startswith("!["):
            output.append(inline(line))
            index += 1
            continue
        paragraph = [line]
        index += 1
        while index < len(lines) and lines[index].strip() and not lines[index].lstrip().startswith(("#", "|", "![")):
            paragraph.append(lines[index].strip())
            index += 1
        output.append("<p>" + inline(" ".join(paragraph)) + "</p>")
    return "\n".join(output)


def page(title: str, body: str, source: str) -> str:
    return f"""<!doctype html>
<html lang="zh-Hant">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
:root {{ font-family: system-ui, -apple-system, "Noto Sans TC", sans-serif; color: #17233b; background: #f3f6fb; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; }}
main {{ max-width: 860px; margin: 32px auto; padding: 32px; background: white; border-radius: 16px; line-height: 1.75; }}
h1,h2,h3 {{ line-height: 1.35; }} h2 {{ margin-top: 2em; border-bottom: 1px solid #dce4ef; padding-bottom: .25em; }}
img {{ display: block; max-width: 100%; height: auto; margin: auto; }} figure {{ margin: 1.5em 0; }} figcaption {{ text-align: center; color: #59687e; font-size: .9em; }}
.table-wrap {{ overflow-x: auto; }} table {{ border-collapse: collapse; width: 100%; }} th,td {{ border-bottom: 1px solid #dce4ef; padding: 7px 10px; text-align: left; }}
a {{ color: #1765ba; }} code {{ background: #edf2f8; padding: 1px 4px; border-radius: 4px; }} .source {{ color: #59687e; font-size: .9rem; }}
@media(max-width: 600px) {{ main {{ margin: 0; padding: 20px; border-radius: 0; }} }}
</style></head>
<body><main><nav><a href="../index.html">← 返回首頁</a></nav>
<p class="source">本頁由既有 <code>{html.escape(source)}</code> 轉換；內容數字未重新計算。</p>
<article>{body}</article></main></body></html>
"""


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    FIGURES.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    metrics = {}
    for name, source in METRIC_SOURCES.items():
        metrics[name] = {
            "source": source,
            "metrics": json.loads((ROOT / source).read_text(encoding="utf-8")),
        }
    (DOCS / "results.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    copied = []
    for source in sorted(RESULTS.rglob("*.png")):
        relative = source.relative_to(RESULTS)
        target = FIGURES / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        copied.append(f"{source.relative_to(ROOT)} -> {target.relative_to(ROOT)}")

    for name, source in PAPER_SOURCES.items():
        markdown = (ROOT / source).read_text(encoding="utf-8")
        title = markdown.splitlines()[0].removeprefix("# ")
        target = REPORTS / f"{name}.html"
        target.write_text(page(title, render_markdown(markdown), source), encoding="utf-8")
        copied.append(f"{source} -> {target.relative_to(ROOT)}")

    for item in copied:
        print(item)
    print("results/metrics.json + results/ai4i/metrics.json -> docs/results.json")


if __name__ == "__main__":
    main()
