"""Export the same reviewed Markdown snapshot to PDF and EPUB 3.

No source files are modified. Requires Pandoc; PDF also needs XeLaTeX and
Noto Serif CJK TC; EPUB validation uses EPUBCheck and Java.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
WORK = ROOT / "tmp" / "pdfs"
# Protect fenced/inline code, math, and existing links from prose rewrites.
PROTECTED = re.compile(
    r"(```[\s\S]*?```|~~~[\s\S]*?~~~|`[^`\n]+`|\$\$[\s\S]*?\$\$|"
    r"\$(?:\\.|[^$\n\\])+?\$|!?\[(?:[^\[\]\n]|\[[^\]\n]*\])*\]\([^\)\n]*\))"
)
DISPLAY = re.compile(r"\$\$\s*([\s\S]*?)\s*\$\$")
TAG = re.compile(r"\\tag\{(\d+)\}")


def run(command: list[str], *, data: str | None = None) -> str:
    result = subprocess.run(command, input=data, text=True, encoding="utf-8",
                            errors="replace", capture_output=True, cwd=ROOT)
    if result.stderr.strip():
        print(result.stderr, file=sys.stderr)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {command[0]}\n{result.stdout}")
    return result.stdout


def locate(name: str, pattern: str, explicit: str | None = None) -> str:
    if explicit:
        candidate = Path(explicit).expanduser().resolve()
        if candidate.is_file():
            return str(candidate)
        raise FileNotFoundError(candidate)
    local = sorted((ROOT / ".tools").glob(pattern))
    if local:
        return str(local[0])
    found = shutil.which(name)
    if found:
        return found
    raise FileNotFoundError(f"Missing {name}; see docs/EXPORT.md for setup instructions.")


def map_prose(text: str, transform) -> str:
    return "".join(part if i % 2 else transform(part)
                   for i, part in enumerate(PROTECTED.split(text)))


def read_bibliography(text: str) -> dict[int, str]:
    entries = {int(n): entry for n, entry in re.findall(r"(?m)^(\d+)\. (.+)$", text)}
    if not entries or sorted(entries) != list(range(1, max(entries) + 1)):
        raise ValueError("Bibliography must have unique contiguous numbers starting at 1")
    if len(entries) != len(re.findall(r"(?m)^\d+\. ", text)):
        raise ValueError("Duplicate bibliography number")
    return entries


def link_prose(text: str, references: set[int], equations: set[int]) -> str:
    def convert(segment: str) -> str:
        def cite(match):
            number = int(match[1])
            if number not in references:
                raise ValueError(f"Missing bibliography entry [{number}]")
            return f"[[{number}]](#bib-{number})"

        segment = re.sub(r"(?<!!)\[([1-9]\d*)\](?!\s*\()", cite, segment)
        def equation(match):
            number = int(match[2])
            if number not in equations:
                raise ValueError(f"Missing equation {number}")
            return f"{match[1]}[{number}](#eq-{number})"
        return re.sub(r"(式\s*[（(]?)(\d+)(?![\d.])", equation, segment)
    return map_prose(text, convert)


def prepare_chapter(text: str, chapter: str, references: set[int], equations: set[int]) -> str:
    # ch06 is the complete version; its inherited second title/provenance note
    # describes the old split files and is not part of the book narrative.
    lines, seen_title, fence = [], False, None
    for line in text.splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            if fence is None:
                fence = marker[1]
            elif marker[1][0] == fence[0] and len(marker[1]) >= len(fence):
                fence = None
            lines.append(line)
            continue
        if fence:
            lines.append(line)
            continue
        if line.startswith("> 譯自 Nathan Lambert"):
            continue
        if line.startswith("# "):
            if seen_title:
                if chapter != "ch06":
                    raise ValueError(f"Unexpected duplicate chapter title: {chapter}")
                continue
            seen_title = True
            line += f" {{#{chapter}}}"
        lines.append(line)
    if not seen_title:
        raise ValueError(f"Missing chapter title: {chapter}")
    text = "\n".join(lines)
    text = link_prose(text, references, equations)
    # Preserve original figure numbering/captions, with valid native figure IDs.
    text = re.sub(
        r"!\[圖\]\((figures/[^)]+)\)[ \t]*\n(?:[ \t]*\n)*\*圖\s*(\d+)[：:]([^\n]+)\*",
        lambda m: f"![圖 {m[2]}：{m[3]}]({m[1]}){{#fig-{m[2]}}}", text)

    # Pandoc's AST retains these IDs in PDF and across split EPUB chapters.
    def mark_equation(match):
        body = match[1]
        tag = TAG.search(body)
        if not tag:
            return match[0]
        return (f'::: {{#eq-{tag[1]} .equation data-number="{tag[1]}"}}\n\n'
                f"$$\n{body}\n$$\n\n:::")
    # Display math inside code examples must remain untouched.
    chunks = re.split(r"(```[\s\S]*?```|~~~[\s\S]*?~~~)", text)
    return "".join(part if i % 2 else DISPLAY.sub(mark_equation, part)
                   for i, part in enumerate(chunks)) + "\n"


def bibliography_markdown(entries: dict[int, str]) -> str:
    lines = ["# 參考文獻 {#bibliography}", "",
             "文獻條目保留原文與既有編號，內文引用可直接跳轉至本節。", ""]
    for number, entry in entries.items():
        entry = map_prose(entry, lambda part: re.sub(
            r"(?<=doi: )(10\.\d{4,9}/[^\s]+?)(?=[.,;]?(?:\s|$))",
            lambda m: f"<https://doi.org/{m[0]}>", part))
        # The bracketed bibliography label is not itself a citation.
        # ref-* is reserved by Pandoc's LaTeX writer for citeproc bibitems.
        lines.extend([f"::: {{#bib-{number} .reference}}", "",
                      f"[{number}] {entry}", "", ":::", ""])
    return "\n".join(lines)


def provenance(config: dict) -> dict:
    digest = hashlib.sha256()
    for path in sorted(CONTENT.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(ROOT).as_posix().encode())
            payload = path.read_bytes()
            if path.suffix == ".md":
                payload = payload.replace(b"\r\n", b"\n")
            digest.update(b"\0" + payload)
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    date = datetime.fromtimestamp(int(epoch), timezone.utc) if epoch else datetime.now(timezone.utc)
    return {"edition_version": config["version"], "source_commit": run(["git", "rev-parse", "HEAD"]).strip(),
            "working_tree_dirty": bool(run(["git", "status", "--porcelain"]).strip()),
            "content_sha256": digest.hexdigest(), "build_date": date.strftime("%Y-%m-%d"),
            "translation_commit": config["translation_commit"],
            "imported_revision": config["imported_revision"],
            "english_candidate_release": config["english_candidate_release"],
            "english_candidate_commit": config["english_candidate_commit"],
            "english_translation_match": config["english_translation_match"]}


def frontmatter(config: dict, info: dict) -> str:
    state = "（含尚未提交的建置修改）" if info["working_tree_dirty"] else ""
    return f'''# 關於本版 {{#edition-notes}}

本書為《Reinforcement Learning from Human Feedback》的正體中文翻譯與增修版本，並非原作者或翻譯社群的官方出版品。

- **原書**：Nathan Lambert 與貢獻者，[natolambert/rlhf-book](https://github.com/natolambert/rlhf-book)。
- **正體中文翻譯**：Twinkle AI Community，[ai-twinkle/rlhf-book-zh-tw](https://github.com/ai-twinkle/rlhf-book-zh-tw)。
- **增修與電子書製作**：[Yi-Wei Chen](https://yiwei-chen.github.io/)。
- **版本**：{config["version"]}；建置日期：{info["build_date"]}。
- **授權**：[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh-hant)，保留署名、非商業使用、相同方式分享。

本版以既有正體中文內容為基礎，加入電子書排版、文獻與公式跳轉。原翻譯宣告依據為 {config["english_edition_date"]} 版；英文來源可能對應 {config["english_candidate_release"]}，但精確對應**尚未確認**，不宣稱已同步最新英文內容。

本書保留原有章節、插圖與公式編號。網頁互動實驗不嵌入電子書，可至[既有線上閱讀網站]({config["website"]})使用；網站與電子書的更新可能不同步。第 6 章只收錄完整稿，不重複收錄分段稿。

## 來源紀錄

增修書稿 commit{state}：\n\n`{info["source_commit"]}`

正體中文內容 SHA-256：\n\n`{info["content_sha256"]}`

翻譯基底 commit：\n\n`{config["translation_commit"]}`

沿用的增修快照 commit：\n\n`{config["imported_revision"]}`

英文候選版本 commit（非已確認翻譯基底）：\n\n`{config["english_candidate_commit"]}`

完整授權條款隨本書附於最後一節。支持原作者請至 [rlhfbook.com](https://rlhfbook.com) 購買實體書。

'''


def prepare(config: dict, info: dict) -> tuple[str, dict]:
    chapters = config["chapters"]
    expected = [f"ch{i:02}" for i in range(1, 18)] + ["appa", "appb", "appc", "bibliography"]
    if chapters != expected:
        raise ValueError("Chapter manifest must include each full chapter exactly once")
    sources = {name: (CONTENT / f"{name}.md").read_text(encoding="utf-8") for name in chapters}
    entries = read_bibliography(sources["bibliography"])
    numbers = []
    for name, text in sources.items():
        if name != "bibliography":
            for match in DISPLAY.finditer(text):
                numbers.extend(int(n) for n in TAG.findall(match[1]))
    if len(set(numbers)) != len(numbers):
        raise ValueError("Duplicate equation numbers")
    parts = [frontmatter(config, info)]
    for chapter in chapters[:-1]:
        parts.append(prepare_chapter(sources[chapter], chapter, set(entries), set(numbers)))
    parts.append(bibliography_markdown(entries))
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    # ASCII decorative rules are not license terms; render them as page-width rules.
    license_text = re.sub(r"(?m)^={5,}$", "\n---\n", license_text)
    parts.append("# 授權條款 {#license}\n\n" + license_text)
    notices = (ROOT / "licenses" / "README.md").read_text(encoding="utf-8")
    notices = notices.replace("# 電子書工具與字型署名", "# 電子書工具與字型署名 {#third-party-notices}")
    parts.append(notices)
    for title, filename in [("Noto 字型：SIL Open Font License 1.1", "Noto-OFL-1.1.txt"),
                            ("MathJax：Apache License 2.0", "MathJax-APACHE-2.0.txt")]:
        terms = (ROOT / "licenses" / filename).read_text(encoding="utf-8")
        # Strip presentation indentation to avoid treating the entire license as code.
        terms = "\n".join(line.lstrip() for line in terms.splitlines())
        parts.append(f"## {title}\n\n{terms}")
    stats = {"chapters": chapters, "references": len(entries), "numbered_equations": len(numbers),
             "equation_numbers": sorted(numbers)}
    return "\n\n".join(parts), stats


def epub_ast(node):
    if isinstance(node, dict):
        if node.get("t") == "Math":
            node["c"][1] = TAG.sub("", node["c"][1]).strip()
        if node.get("t") == "Div" and "equation" in node["c"][0][1]:
            number = dict(node["c"][0][2])["data-number"]
            node["c"][1].append({"t": "Para", "c": [{"t": "Span", "c": [
                ["", ["equation-number"], []], [{"t": "Str", "c": f"({number})"}]]}]})
        for value in node.values():
            epub_ast(value)
    elif isinstance(node, list):
        for value in node:
            epub_ast(value)


def iter_nodes(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from iter_nodes(value)
    elif isinstance(node, list):
        for value in node:
            yield from iter_nodes(value)


def iter_visible_nodes(node):
    """Image alt text duplicates native figure captions; it is not rendered math."""
    if isinstance(node, dict):
        yield node
        if node.get("t") != "Image":
            for value in node.values():
                yield from iter_visible_nodes(value)
    elif isinstance(node, list):
        for value in node:
            yield from iter_visible_nodes(value)


def render_epub_math(ast: dict) -> int:
    formulas = {}
    for node in iter_visible_nodes(ast):
        if node.get("t") == "Math":
            display = node["c"][0]["t"] == "DisplayMath"
            tex = node["c"][1]
            identifier = hashlib.sha256(f"{display}:{tex}".encode()).hexdigest()[:24]
            formulas[identifier] = {"id": identifier, "display": display, "tex": tex}
    manifest = WORK / "math-input.json"
    manifest.write_text(json.dumps(list(formulas.values()), ensure_ascii=False), encoding="utf-8")
    directory = WORK / "math"
    nodejs = shutil.which("node")
    if not nodejs:
        raise FileNotFoundError("Node.js is required to render EPUB math")
    print(run([nodejs, str(ROOT / "scripts" / "render_math.cjs"), str(manifest), str(directory)]).strip())
    dimensions = json.loads((directory / "dimensions.json").read_text(encoding="utf-8"))
    count = 0
    for node in list(iter_visible_nodes(ast)):
        if node.get("t") != "Math":
            continue
        display = node["c"][0]["t"] == "DisplayMath"
        tex = node["c"][1]
        identifier = hashlib.sha256(f"{display}:{tex}".encode()).hexdigest()[:24]
        size = dimensions[identifier]
        classes = ["math-display" if display else "math-inline"]
        style = f'width:{size["width"]:.4f}em;vertical-align:{size["baseline"]:.4f}em'
        node.update({"t": "Image", "c": [["", classes, [["style", style]]],
                    [{"t": "Str", "c": tex}], [(directory / f"{identifier}.svg").as_posix(), ""]]})
        count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=["all", "pdf", "epub"], default="all")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--pandoc")
    parser.add_argument("--xelatex")
    parser.add_argument("--font-dir", type=Path, default=ROOT / ".tools" / "fonts")
    args = parser.parse_args()
    config = json.loads((ROOT / "book.json").read_text(encoding="utf-8"))
    info = provenance(config)
    markdown, stats = prepare(config, info)
    WORK.mkdir(parents=True, exist_ok=True)
    manuscript = WORK / "manuscript.md"
    manuscript.write_text(markdown, encoding="utf-8", newline="\n")
    info["inventory"] = stats
    info["artifacts"] = {}
    if args.prepare_only:
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        return 0
    pandoc = locate("pandoc", "pandoc/**/pandoc.exe", args.pandoc)
    info["pandoc"] = run([pandoc, "--version"]).splitlines()[0]
    ast = json.loads(run([pandoc, str(manuscript), "--from",
                         "markdown+east_asian_line_breaks+autolink_bare_uris-smart", "--to", "json"]))
    info["inventory"]["math_expressions"] = sum(n.get("t") == "Math" for n in iter_visible_nodes(ast))
    metadata = {"title": config["title"], "subtitle": f'正體中文翻譯 (非官方) · {config["version"]}',
                "author": config["author"], "date": info["build_date"], "toc-title": "目錄",
                "lang": config["language"], "rights": "CC BY-NC-SA 4.0",
                "identifier": f'urn:rlhf-book-zhtw-edition:{config["version"]}:{info["content_sha256"]}',
                "font-dir": "`" + args.font_dir.resolve().as_posix() + "`{=latex}",
                "edition": config["version"]}
    meta = WORK / "metadata.json"
    meta.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    ast_path = WORK / "manuscript.json"
    ast_path.write_text(json.dumps(ast, ensure_ascii=False), encoding="utf-8")
    common = [pandoc, "--from=json", "--standalone", "--toc", "--toc-depth=2",
              "--data-dir=" + str(ROOT / "templates"),
              "--resource-path=" + str(CONTENT), "--metadata-file=" + str(meta),
              "--syntax-highlighting=none"]
    stem = f'rlhf-book-zh-tw-{config["version"]}'
    if args.format in ("all", "epub"):
        epub = copy.deepcopy(ast)
        epub_ast(epub)
        info["inventory"]["epub_math_images"] = render_epub_math(epub)
        info["mathjax"] = json.loads((ROOT / ".tools/mathjax/node_modules/mathjax-full/package.json").read_text())["version"]
        output = ROOT / "output" / "epub" / f"{stem}.epub"
        output.parent.mkdir(parents=True, exist_ok=True)
        run(common + ["--to=epub3", "--split-level=1",
                      "--css=" + str(ROOT / "templates" / "epub.css"), "--output=" + str(output)],
            data=json.dumps(epub, ensure_ascii=False))
        print(f"Created {output}")
        info["artifacts"]["epub"] = {"sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
    if args.format in ("all", "pdf"):
        xelatex = locate("xelatex", "tex/**/xelatex.exe", args.xelatex)
        info["xelatex"] = run([xelatex, "--version"]).splitlines()[0]
        if not (args.font_dir / "NotoSerifCJKtc-Regular.otf").is_file():
            raise FileNotFoundError("Missing static CJK fonts; see docs/EXPORT.md")
        output = ROOT / "output" / "pdf" / f"{stem}.pdf"
        output.parent.mkdir(parents=True, exist_ok=True)
        template = "--template=" + str(ROOT / "templates" / "pdf.tex")
        run(common + [str(ast_path), "--to=latex", "--top-level-division=chapter", template,
                      "--output=" + str(WORK / "book.tex")])
        options = ["--pdf-engine-opt=--enable-installer"] if "MiKTeX" in info["xelatex"] else []
        run(common + [str(ast_path), "--top-level-division=chapter", template,
                      "--pdf-engine=" + xelatex, *options, "--output=" + str(output)])
        print(f"Created {output}")
        info["artifacts"]["pdf"] = {"sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
    report = ROOT / "output" / "build-provenance.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, FileNotFoundError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
