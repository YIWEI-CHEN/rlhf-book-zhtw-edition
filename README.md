# RLHF - 從人類回饋中強化學習 (增修版)

這是一份以閱讀、修訂與電子書出版為目的的正體中文書稿專案。正文沿用 ai-twinkle 的翻譯，納入既有內容修正，提供 PDF 與 EPUB，並逐步整理原書程式碼的正體中文使用說明。


## 作者與來源

原書 **Reinforcement Learning from Human Feedback** 由 **Nathan Lambert 與貢獻者**撰寫，請參閱 [英文原書網站](https://rlhfbook.com)及 [其Github](https://github.com/natolambert/rlhf-book)。

正體中文翻譯來自 **Twinkle AI Community** 的 [ai-twinkle/rlhf-book-zh-tw](https://github.com/ai-twinkle/rlhf-book-zh-tw)。本專案在其內容上增修，由 [Yi-Wei Chen](https://yiwei-chen.github.io/) 維護，並非原作者或 Twinkle AI 的官方版本。

## 閱讀與下載

- [線上閱讀](https://yiwei-chen.github.io/rlhf-book-zh-tw/)：既有 HTML 網站，正體中文與互動網站基於 ai-twinkle；網站由另一個 repo 維護，與本 repo 不會自動同步。
- [章節書稿](content/)：可直接在 GitHub 閱讀或下載修改，插圖存放於 `content/figures/`。
- [下載 PDF（v0.1）](https://github.com/YIWEI-CHEN/rlhf-book-zhtw-edition/releases/download/v0.1/rlhf-book-zh-tw-v0.1.pdf)：固定版面，內嵌正體中文字型。
- [下載 EPUB（v0.1）](https://github.com/YIWEI-CHEN/rlhf-book-zhtw-edition/releases/download/v0.1/rlhf-book-zh-tw-v0.1.epub)：可重排文字，適合電子書閱讀器。
- [v0.1 發布說明](https://github.com/YIWEI-CHEN/rlhf-book-zhtw-edition/releases/tag/v0.1)：包含建置來源紀錄與 [SHA-256 校驗碼](https://github.com/YIWEI-CHEN/rlhf-book-zhtw-edition/releases/download/v0.1/SHA256SUMS.txt)。其他版本見 [Releases](https://github.com/YIWEI-CHEN/rlhf-book-zhtw-edition/releases)。


## 產生 PDF 與 EPUB

需要 Python 3.10+、Node.js 18+ 與 XeLaTeX。Windows 可使用 MiKTeX；安裝與其他平台說明見 [電子書建置指南](docs/EXPORT.md)。

```powershell
# 首次準備：下載固定版本的工具與字型至本機 .tools/
python scripts/bootstrap_tools.py

# 書稿修改後：同時產生兩種格式
python scripts/export_book.py
```

輸出位置（以下以 [book.json](book.json) 目前的 `v0.1` 為例，檔名會隨版本設定變更）：

- `output/pdf/rlhf-book-zh-tw-v0.1.pdf`
- `output/epub/rlhf-book-zh-tw-v0.1.epub`
- `output/build-provenance.json`：最近一次成功建置的 Git commit、未提交修改狀態、來源 commit SHA、內容與輸出檔雜湊，以及工具版本。

兩種格式均提供中英文封面、目錄、文獻與公式跳轉，以及〈關於本版〉中的作者、譯者、來源連結與授權資訊。完整授權條款與工具、字型署名保留於本 repo 的 [LICENSE](LICENSE) 與 [licenses/](licenses/)，不另收錄為電子書章節。

PDF 使用內嵌正體中文字型；EPUB 使用離線 SVG 公式，不依賴閱讀器執行 JavaScript。EPUB 的字型與分頁由閱讀器決定，長公式建議使用橫向畫面或較大螢幕；公式替代文字保留 TeX，尚未提供完整的語音數學朗讀。

## 內容版本

| 來源 | 記錄 |
|---|---|
| ai-twinkle 翻譯基底 | [`41834be9275d000a864e275a7347e7e13941536e`](https://github.com/ai-twinkle/rlhf-book-zh-tw/commit/41834be9275d000a864e275a7347e7e13941536e) |
| 本次沿用的增修快照 | [`9a27262290854adb9cab5515916591965600af5d`](https://github.com/YIWEI-CHEN/rlhf-book-zh-tw/commit/9a27262290854adb9cab5515916591965600af5d) |

以上 SHA 用於標示內容出處。

`content/ch06.md` 是第 6 章完整內容；`ch06a.md`、`ch06b.md` 是保留的分段稿，電子書不重複收錄。章節順序與版本集中記錄於 [book.json](book.json)。

## 引用（Citation）

請依使用的版本選用以下 BibTeX 引用格式。

### 正體中文版

```bibtex
@misc{lambert2025rlhfzhtw,
  title      = {Reinforcement Learning from Human Feedback},
  zhtw_title = {RLHF - 從人類回饋中強化學習 (增修版)},
  author     = {Nathan Lambert},
  year       = {2025},
  url        = {https://github.com/YIWEI-CHEN/rlhf-book-zhtw-edition},
  translator = {{Twinkle AI Community}},
  editor     = {Chen, Yi-Wei},
}
```

### 英文網頁與 arXiv 版

引用英文網頁或 arXiv 版本時，使用 arXiv 的引用格式：

```bibtex
@misc{lambert2025reinforcementlearninghumanfeedback,
  title         = {Reinforcement Learning from Human Feedback},
  author        = {Nathan Lambert},
  year          = {2025},
  eprint        = {2504.12501},
  archivePrefix = {arXiv},
  primaryClass  = {cs.LG},
  url           = {https://arxiv.org/abs/2504.12501},
}
```

### Manning 版

```bibtex
@book{lambert2026reinforcement,
  author    = {Nathan Lambert},
  title     = {Reinforcement Learning from Human Feedback: Alignment and post-training of {LLMs}},
  year      = {2026},
  publisher = {Manning Publications},
  isbn      = {9781633434301},
  url       = {https://www.manning.com/books/reinforcement-learning-from-human-feedback},
}
```

## 參與修訂

歡迎提出錯字、翻譯、公式與引用問題。請註明章節、原句，以及可核對的英文來源；翻譯修正與新版英文內容同步應分開記錄。

## 授權

書稿與翻譯沿用 **[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh-hant)**，完整條款見 [LICENSE](LICENSE)。散布增修內容時須保留原作者、翻譯社群與來源署名，說明修改，遵守非商業及相同方式分享條件。

未來匯入的程式碼保留各自原有授權、copyright 與 notices，不以書稿授權覆蓋程式碼授權。支持原作者可至 [rlhfbook.com](https://rlhfbook.com) 購買實體書。
