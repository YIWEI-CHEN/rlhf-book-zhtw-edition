# PDF／EPUB 建置指南

同一份 `content/` 書稿產生 PDF 與 EPUB，不改寫來源 Markdown、不引入網站程式。設定集中在 `book.json`；本版為 `v0.1`，英文翻譯基底仍標為未確認，不把候選 `book/v0.10` 宣稱為已驗證來源。

## 1. 準備環境

- Python 3.10+（建置主程式只使用標準函式庫）。
- Node.js 18+ 與 npm，用於 EPUB 的 MathJax SVG 公式；單獨產生 PDF 不需要 Node.js。
- XeLaTeX：Windows 可用 MiKTeX，其他平台可用 TeX Live。需要 `xeCJK`、`fontspec`、`unicode-math`、`amsmath`、`adjustbox`、`fvextra`、`caption`、`fancyhdr`、`xurl`、`hyperref`、`bookmark` 等套件，以及 TeX Gyre／Latin Modern 字型。MiKTeX 建置時啟用缺少套件的自動安裝，因此首次 PDF 建置需要網路。

在 repo 根目錄執行：

```powershell
python scripts/bootstrap_tools.py
```

這會下載固定版本的 Pandoc 3.11（Windows x64）、EPUBCheck 5.3.0、Java 21 執行環境（Windows x64）、Noto Serif CJK TC Regular／Bold，以及 MathJax 3.2.2。工具只放在忽略的 `.tools/`，不更改系統 PATH，也不自動安裝或更新 TeX 發行版。

下載的 ZIP 與字型逐一核對 SHA-256。MathJax 依 `tooling/mathjax/package-lock.json` 安裝，停用 npm 安裝腳本，並將間接相依的 xmldom 固定在已修補的 0.9.12。工具及字型出處見 [licenses](../licenses/README.md)。

macOS／Linux：先自行安裝 Pandoc 3.11、Java 11+、Node.js 與具備上述套件的 TeX Live，再執行 bootstrap；它會略過 Windows 的 Pandoc／Java 下載。其他平台路徑已保留支援，但本版實際建置驗證環境為 Windows x64。

若只需要 PDF，可使用 `python scripts/bootstrap_tools.py --skip-mathjax`。指定既有工具：

```powershell
python scripts/export_book.py --pandoc C:/tools/pandoc.exe --xelatex C:/tools/xelatex.exe --font-dir C:/fonts/noto
```

字型目錄需有 `NotoSerifCJKtc-Regular.otf` 與 `NotoSerifCJKtc-Bold.otf`。預設先找 `.tools/`，再找 PATH；顯式工具路徑優先。

## 2. 建置

```powershell
python scripts/export_book.py                # 同時產生 PDF 和 EPUB
python scripts/export_book.py --format pdf   # 只產生 PDF
python scripts/export_book.py --format epub  # 只產生 EPUB
python scripts/export_book.py --prepare-only # 只組稿並檢查編號
```

建置預設不發布、不 push、不修改 `content/`。書稿改好後重跑一次即可；不需要逐章分開建置。

| 路徑 | 用途 |
|---|---|
| `output/pdf/rlhf-book-zh-tw-v0.1.pdf` | A4、11 pt、內嵌字型、可選取文字與公式 |
| `output/epub/rlhf-book-zh-tw-v0.1.epub` | EPUB 3，可重排文字、內嵌 SVG 公式 |
| `output/build-provenance.json` | 本次建置來源、整個 content 目錄雜湊、工具版本與內容統計 |
| `tmp/pdfs/` | 中間 Markdown、Pandoc JSON、LaTeX、SVG 與 QA 圖片 |

建置日期使用 UTC；可設定 `SOURCE_DATE_EPOCH` 固定文件日期。這不保證不同 TeX／作業系統環境的輸出位元組完全相同。若工作目錄有未提交的修改，書內來源頁會明確標示。

`build-provenance.json` 描述**最近一次成功執行的建置**。發布兩種格式前務必執行預設的完整建置，再驗證，不混用不同時間的單一格式輸出。

## 3. 內容如何轉換

- 收錄第 1–17 章、附錄 A–C、參考文獻；第 6 章只用完整 `ch06.md`，不加入 `ch06a.md`／`ch06b.md`。輸出時移除合併稿中重複的第 6 章標題及每章舊來源註記，統一記錄在書首。
- 保留既有的 409 筆參考文獻、158 個公式編號與插圖內容，不重新編號。引用 `[N]` 及「式 N」變成內部連結；不重寫程式碼、數學內容或既有 Markdown 連結。DOI 條目增加可跳轉 URL。
- PDF 交由 Pandoc 與 XeLaTeX 排版；EPUB 公式由 MathJax 轉為內嵌 SVG，避免閱讀器不支援 MathML 而顯示原始 TeX。SVG 使用局部字形快取，離線可用；原始 TeX 保留在替代文字中。
- 電子書不包含網站的互動實驗。PDF／EPUB 與既有 Pages 是不同發布管線，不會自動同步。
- 原授權條款完整附於書末；ASCII 分隔線只轉成適合頁寬的橫線。另附字型與公式工具署名及相應授權。

## 4. 測試與發布檢查

首次準備檢查環境：

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
```

已有 uv 時也可用 `uv venv .venv` 與 `uv pip install --python .venv/Scripts/python.exe -r requirements-dev.txt`。macOS／Linux 使用 `.venv/bin/python`。

每次發布前：

```powershell
python -m unittest discover -s tests -v
python scripts/export_book.py
.venv/Scripts/python.exe scripts/validate_exports.py --render
```

測試分層：

1. 單元測試：保護程式碼與公式、引用與公式的遺失目標、文獻編號重複、章節清單及第 6 章去重、SVG 公式編號、DOI 連結。
2. EPUB：ZIP／XML、章節及每個文獻／公式 ID、內部連結與圖片資源、公式數量、原插圖雜湊，以及 EPUBCheck 零錯誤、零警告。
3. PDF：章節書籤、每筆內部連結有有效目標頁、參考文獻完整性、公式編號、替代字元與頁邊越界。回歸案例核對 `[111]` 指向 Ahmadian 的條目。
4. 人工視覺檢查：`--render` 將封面、目錄、各章起始頁和第 6／8 章公式頁輸出到 `tmp/pdfs/qa/`。另抽查長表格、程式碼、授權頁及 EPUB 橫直向顯示；程式通過不代表排版或數學語義已全部審校。

檢查結果寫入 `output/validation.json`，檔案雜湊寫入 `output/SHA256SUMS.txt`。發布前先 commit 書稿與建置工具，再於乾淨工作目錄重建，執行 `validate_exports.py --release --render`，確保書內 commit 可追溯。

PDF／EPUB、provenance 與 SHA256SUMS 適合放入 GitHub Release；不要將下載工具、中間檔或本機 `AGENTS.md` 提交至 repo。是否發布由維護者決定，腳本不會自動執行 GitHub 寫入。

## 5. 已知差異與排錯

- EPUB 字型、換行和分頁取決於閱讀器；長公式在窄螢幕可能縮小，建議橫向閱讀。公式保留 TeX 替代文字，但尚未做到完整語音數學朗讀。
- 書中模型輸出／提示範例若原本是程式碼區塊，其 `**` 等 Markdown 記號會照原樣保留，不當作正文排版。
- PDF 首次建置較慢，MiKTeX 可能下載缺少的套件。若提示缺套件或字型，先用 MiKTeX Console 處理，再重跑；勿混用不相容的 TeX 套件版本。
- 本機 MiKTeX 可能提示尚未檢查更新。它與缺字、未定義連結、LaTeX 建置失敗是不同問題；驗證時仍須檢查實際輸出。
- 失敗時查看終端訊息與 `tmp/pdfs/book.tex`；修復後完整重建。不要把先前成功留下的檔案當成新版本。

工具參考：[Pandoc 手冊](https://pandoc.org/MANUAL.html)、[MathJax Node 使用說明](https://docs.mathjax.org/en/v3.2/server/start.html)、[EPUBCheck](https://github.com/w3c/epubcheck)。
