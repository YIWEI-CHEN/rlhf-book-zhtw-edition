"""Check ebook structure, content inventory and links; optionally render QA pages."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import posixpath
import re
import subprocess
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET
import zipfile

from export_book import ROOT, CONTENT, locate, iter_nodes


def require(condition, message):
    if not condition:
        raise ValueError(message)


def presentation_checks(config: dict, cover: str, notes: str, urls: set[str]):
    compact = lambda text: re.sub(r"\s+", "", text)
    for text in ("RLHF", "從人類回饋中強化學習", config["subtitle"], config["english_title"],
                 config["english_subtitle"], "作者", config["author"], "譯者", config["translator"], config["editor"]):
        require(compact(text) in compact(cover), f"Cover text missing: {text}")
    for text in ("正體中文翻譯", "非官方", "與貢獻者"):
        require(compact(text) not in compact(cover), f"Obsolete cover text: {text}")
    for text in ("原著", "中文翻譯", "輸出日期", "CC BY-NC-SA 4.0"):
        require(compact(text) in compact(notes), f"Edition note missing: {text}")
    for text in ("來源紀錄", "建置日期", "原翻譯宣告依據", "精確對應", "既有線上閱讀網站",
                 "第 6 章只收錄完整稿", "完整授權條款隨本書附於最後一節", "保留署名、非商業使用、相同方式分享"):
        require(compact(text) not in compact(notes), f"Obsolete edition note: {text}")
    require("https://apps.twinkleai.tw/rlhf-book-zh-tw/" in urls, "Twinkle website link missing")


def epub_checks(path: Path, inventory: dict, config: dict) -> dict:
    with zipfile.ZipFile(path) as bundle:
        require(bundle.testzip() is None, "EPUB ZIP CRC failed")
        require(bundle.namelist()[0] == "mimetype", "EPUB mimetype must be first")
        require(bundle.getinfo("mimetype").compress_type == zipfile.ZIP_STORED, "Compressed mimetype")
        require(bundle.read("mimetype") == b"application/epub+zip", "Wrong EPUB mimetype")
        names = set(bundle.namelist())
        documents = {n: ET.fromstring(bundle.read(n)) for n in names if n.endswith((".xhtml", ".svg"))}
        ids, all_ids = {}, Counter()
        for name, tree in documents.items():
            values = [e.attrib["id"] for e in tree.iter() if "id" in e.attrib]
            require(len(values) == len(set(values)), f"Duplicate ID in {name}")
            ids[name] = set(values)
            if name.endswith(".xhtml"):
                all_ids.update(values)
        for identifier in inventory["chapters"] + ["edition-notes"]:
            require(all_ids[identifier] == 1, f"Chapter ID missing/duplicated: {identifier}")
        require(not all_ids["license"] and not all_ids["third-party-notices"], "Removed back-matter chapters were included")
        container = ET.fromstring(bundle.read("META-INF/container.xml"))
        package_path = next(element.attrib["full-path"] for element in container.iter()
                            if element.tag.endswith("}rootfile"))
        package = ET.fromstring(bundle.read(package_path))
        manifest = {element.attrib["id"]: posixpath.normpath(posixpath.join(posixpath.dirname(package_path), element.attrib["href"]))
                    for element in package.iter() if element.tag.endswith("}item")}
        spine = [manifest[element.attrib["idref"]] for element in package.iter() if element.tag.endswith("}itemref")]
        chapter_order = [element.attrib["id"] for name in spine for element in documents[name].iter()
                         if element.attrib.get("id") in inventory["chapters"]]
        require(chapter_order == inventory["chapters"], "EPUB reading order differs from the chapter manifest")
        titlepage = next(element for tree in documents.values() for element in tree.iter()
                         if element.tag.endswith("}section")
                         and element.attrib.get("{http://www.idpf.org/2007/ops}type") == "titlepage")
        notes = next(tree for name, tree in documents.items() if "edition-notes" in ids[name])
        presentation_checks(config, " ".join(titlepage.itertext()), " ".join(notes.itertext()),
                            {element.attrib["href"] for element in notes.iter() if "href" in element.attrib})
        navigation = next(element for tree in documents.values() for element in tree.iter()
                          if element.tag.endswith("}nav")
                          and element.attrib.get("{http://www.idpf.org/2007/ops}type") == "toc")
        nav_labels = [" ".join(element.itertext()).strip() for element in navigation.iter() if element.tag.endswith("}a")]
        require(any(label.startswith("1.6.1 ") for label in nav_labels), "EPUB TOC is missing third-level sections")
        require(not any(label.startswith("1.6.1.1 ") for label in nav_labels), "EPUB TOC includes unwanted fourth level")
        require(all("原著內容依" not in " ".join(tree.itertext()) for name, tree in documents.items()
                    if name.endswith(".xhtml")), "Obsolete chapter license note")
        require(not all_ids["ch06a"] and not all_ids["ch06b"], "Split chapter 6 was included")
        for number in range(1, inventory["references"] + 1):
            require(all_ids[f"bib-{number}"] == 1, f"Bibliography target missing: {number}")
        for number in inventory["equation_numbers"]:
            require(all_ids[f"eq-{number}"] == 1, f"Equation target missing: {number}")
        checked, math_images = 0, 0
        for name, tree in documents.items():
            for element in tree.iter():
                require(not element.tag.endswith("}math"), "Unexpected MathML fallback")
                require("script" != element.tag.split("}")[-1], "EPUB must not require JavaScript")
                if element.tag.endswith("}img") and "math-" in element.attrib.get("class", ""):
                    math_images += 1
                    require(bool(element.attrib.get("alt")), "Formula image is missing alternative text")
                for key, value in element.attrib.items():
                    if key.split("}")[-1] not in ("src", "href"):
                        continue
                    link = urlsplit(value)
                    if link.scheme or link.netloc:
                        require(key.split("}")[-1] != "src", f"External image: {value}")
                        continue
                    target = posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(link.path))) if link.path else name
                    require(target in names, f"Missing EPUB resource: {name} -> {value}")
                    if link.fragment:
                        require(unquote(link.fragment) in ids.get(target, set()), f"Broken EPUB anchor: {name} -> {value}")
                    checked += 1
        require(math_images == inventory["math_expressions"], f"Math count mismatch: {math_images}")
        ast = json.loads((ROOT / "tmp/pdfs/manuscript.json").read_text(encoding="utf-8"))
        figures = {node["c"][2][0] for node in iter_nodes(ast) if node.get("t") == "Image"}
        packaged = {hashlib.sha256(bundle.read(n)).hexdigest() for n in names if n.endswith(".png")}
        for figure in figures:
            require(hashlib.sha256((CONTENT / figure).read_bytes()).hexdigest() in packaged, f"Missing figure: {figure}")
    java = locate("java", "java/**/bin/java.exe")
    jar = locate("epubcheck.jar", "epubcheck/**/epubcheck.jar")
    result = subprocess.run([java, "-jar", jar, str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(result.stdout, result.stderr)
    require(result.returncode == 0 and "0 errors / 0 warnings" in result.stdout, "EPUBCheck failed or produced warnings")
    return {"internal_resource_links": checked, "math_images": math_images, "figures": len(figures),
            "epubcheck": "5.3.0: 0 errors, 0 warnings"}


def pdf_checks(path: Path, inventory: dict, render: bool, config: dict) -> dict:
    import pymupdf
    document = pymupdf.open(path)
    require(not document.is_encrypted, "PDF unexpectedly encrypted")
    toc = document.get_toc()
    require(len([entry for entry in toc if entry[0] == 1]) == len(inventory["chapters"]) + 1,
            "PDF chapter bookmarks missing/duplicated")
    require(any(entry[0] == 3 and entry[1].startswith("1.6.1 ") for entry in toc), "PDF TOC is missing third-level sections")
    require(max(entry[0] for entry in toc) == 3, "Unexpected PDF bookmark depth")
    pages = [page.get_text() for page in document]
    require(all("\ufffd" not in text for text in pages), "PDF contains replacement characters")
    notes_start = next(entry[2] - 1 for entry in toc if entry[1] == "關於本版")
    notes_end = next(entry[2] - 1 for entry in toc if entry[0] == 1 and entry[2] - 1 > notes_start)
    presentation_checks(config, pages[0], "\n".join(pages[notes_start:notes_end]),
                        {link["uri"] for page in document.pages(notes_start, notes_end)
                         for link in page.get_links() if "uri" in link})
    for page in document.pages(1, notes_start):
        for block in page.get_text("dict")["blocks"]:
            if block["type"] == 0:
                require(all(span["color"] == 0 for line in block["lines"] for span in line["spans"]
                            if span["text"].strip()), "PDF table of contents is not black")
    require(all("原著內容依" not in text and "正體中文翻譯(非官方)" not in re.sub(r"\s+", "", text)
                for text in pages), "Obsolete PDF chapter note/header")
    links = 0
    example_citation = False
    for number, page in enumerate(document):
        textpage = page.get_textpage()
        for link in page.get_links():
            links += 1
            if link["kind"] in (pymupdf.LINK_GOTO, pymupdf.LINK_NAMED):
                require(0 <= link.get("page", -1) < len(document), f"Broken PDF link on page {number + 1}")
                if page.get_textbox(link["from"], textpage=textpage).strip() == "[111]":
                    require("Ahmadian" in pages[link["page"]], "Citation [111] points to wrong page")
                    example_citation = True
        for x0, y0, x1, y1, text, *_ in page.get_text("blocks", textpage=textpage):
            # 40pt safety region allows CJK hanging punctuation, but catches clipped rules/URLs.
            require(40 <= x0 <= x1 <= page.rect.width - 40 and y0 >= 10 and y1 <= page.rect.height - 10,
                    f"PDF text overflow on page {number + 1}: {text[:80]}")
    require(example_citation, "Expected clickable chapter-6 citation [111]")
    require(sum(len(page.get_images()) for page in document) == 49, "PDF figure inventory changed; review expected count")
    start = next(entry[2] - 1 for entry in toc if entry[1] == "參考文獻")
    end = next(entry[2] - 1 for entry in toc if entry[0] == 1 and entry[2] - 1 > start)
    top_level = [entry for entry in toc if entry[0] == 1]
    require(top_level[-4][1] == "參考文獻" and all(entry[1].startswith(f"附錄 {letter}")
                for entry, letter in zip(top_level[-3:], "ABC")), "PDF references must precede appendices A-C")
    labels = [int(x) for x in re.findall(r"\[(\d+)\]", "\n".join(pages[start:end]))]
    require(labels == list(range(1, inventory["references"] + 1)), "PDF bibliography incomplete")
    equation_labels = {int(x) for x in re.findall(r"\((\d+)\)", "\n".join(pages))}
    require(set(inventory["equation_numbers"]) <= equation_labels, "PDF equation labels missing")
    if render:
        directory = ROOT / "tmp/pdfs/qa"
        directory.mkdir(parents=True, exist_ok=True)
        selected = {0, 1, len(document) - 1}
        selected.update(entry[2] - 1 for entry in toc if entry[0] == 1)
        selected.update(i for i, text in enumerate(pages) if any(f"({n})" in text for n in (57, 58, 80, 81, 96)))
        for number in sorted(selected):
            document[number].get_pixmap(matrix=pymupdf.Matrix(1.3, 1.3)).save(directory / f"pdf-{number + 1:03}.png")
        print(f"Rendered {len(selected)} PDF pages for visual review in {directory}")
    return {"pages": len(document), "bookmarks": len(toc), "links": links,
            "references": len(labels), "numbered_equations": len(inventory["equation_numbers"])}


def epub_layout_checks(path: Path, render: bool, viewport: tuple[int, int] = (400, 600)) -> dict:
    import pymupdf
    document = pymupdf.open(path)
    document.layout(width=viewport[0], height=viewport[1])
    directory = ROOT / "tmp/pdfs/qa"
    if render:
        directory.mkdir(parents=True, exist_ok=True)
    checked = 0
    selected = {0, 1}
    selected.update(entry[2] - 1 for entry in document.get_toc() if entry[1] == "關於本版")
    for number, page in enumerate(document):
        blocks = page.get_text("dict")["blocks"]
        images = [pymupdf.Rect(block["bbox"]) for block in blocks if block["type"] == 1
                  and block["bbox"][3] - block["bbox"][1] > 35
                  and block["bbox"][2] - block["bbox"][0] > 120]
        for image in images:
            checked += 1
            for block in blocks:
                if block["type"] != 0:
                    continue
                for line in block["lines"]:
                    overlap = image & pymupdf.Rect(line["bbox"])
                    require(overlap.height <= 3 or overlap.width <= 5,
                            f"EPUB large image/formula overlaps text on reflow page {number + 1}")
        if render and (number in selected or any(f"({n})" in page.get_text().splitlines() for n in (15, 57, 78, 80, 81))):
            page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(directory / f"epub-{viewport[0]}x{viewport[1]}-{number + 1:03}.png")
    return {"reader": f"MuPDF {pymupdf.VersionBind}", "viewport": f"{viewport[0]}x{viewport[1]}",
            "large_images_checked": checked, "large_image_text_overlaps": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", action="store_true", help="Render representative PDF pages for visual review")
    parser.add_argument("--release", action="store_true", help="Require exports built from a clean checkout")
    args = parser.parse_args()
    config = json.loads((ROOT / "book.json").read_text(encoding="utf-8"))
    provenance = json.loads((ROOT / "output/build-provenance.json").read_text(encoding="utf-8"))
    if args.release:
        require(not provenance["working_tree_dirty"], "Release was built from uncommitted changes")
    stem = f'rlhf-book-zh-tw-{config["version"]}'
    paths = {format: ROOT / "output" / format / f"{stem}.{format}" for format in ("pdf", "epub")}
    for format, path in paths.items():
        require(hashlib.sha256(path.read_bytes()).hexdigest() == provenance.get("artifacts", {}).get(format, {}).get("sha256"),
                f"{format} does not match the successful build report; rebuild both formats")
    report = {"epub": epub_checks(paths["epub"], provenance["inventory"], config),
              "pdf": pdf_checks(paths["pdf"], provenance["inventory"], args.render, config),
              "source_commit": provenance["source_commit"], "visual_review": "manual review required; not implied by automated checks"}
    report["epub"]["reflow_check"] = epub_layout_checks(paths["epub"], args.render)
    report["epub"]["landscape_check"] = epub_layout_checks(paths["epub"], args.render, (600, 400))
    for format, path in paths.items():
        report[format]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        report[format]["bytes"] = path.stat().st_size
    (ROOT / "output/validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    checksums = "".join(f'{report[format]["sha256"]}  {path.name}\n' for format, path in paths.items())
    (ROOT / "output/SHA256SUMS.txt").write_text(checksums, encoding="ascii")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
