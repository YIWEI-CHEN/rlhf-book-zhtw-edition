# RLHF - 從人類回饋中強化學習 (增修版)

這是一份以閱讀、修訂與電子書出版為目的的正體中文書稿專案。正文沿用 ai-twinkle 的翻譯，納入既有內容修正，再逐步製作 PDF、EPUB 與原書程式碼的正體中文使用說明。

本 repo 使用全新的 Git 歷史，不包含互動網站程式。書稿來源與作者署名仍完整保留；獨立建庫不代表重新獨立翻譯。

## 作者與來源

原書 **Reinforcement Learning from Human Feedback** 由 **Nathan Lambert 與貢獻者**撰寫，請參閱 [英文原書](https://rlhfbook.com)及 [natolambert/rlhf-book](https://github.com/natolambert/rlhf-book)。

正體中文翻譯來自 **Twinkle AI Community** 的 [ai-twinkle/rlhf-book-zh-tw](https://github.com/ai-twinkle/rlhf-book-zh-tw)。本專案在其內容上增修，由 [Yi-Wei Chen](https://yiwei-chen.github.io/) 維護，並非原作者或 Twinkle AI 的官方版本。

## 閱讀與下載

- [線上閱讀](https://yiwei-chen.github.io/rlhf-book-zh-tw/)：既有 HTML 網站，正體中文與互動網站基於 ai-twinkle；網站由另一個 repo 維護，與本 repo 不會自動同步。
- [章節書稿](content/)：可直接在 GitHub 閱讀或下載修改，插圖存放於 `content/figures/`。
- PDF／EPUB：已加入本機建置工具，第一版為 **`v0.1`**。輸出檔名為 `rlhf-book-zh-tw-v0.1.pdf` 與 `rlhf-book-zh-tw-v0.1.epub`；公開下載檔案以 [Releases](https://github.com/YIWEI-CHEN/rlhf-book-zhtw-edition/releases) 實際發布內容為準。

本 repo 不包含 `webapp/` 或 `build.py`，也尚未匯入官方 `code/`。後續匯入程式碼時，保留原英文 `README.md`，另寫 `README.zh-TW.md`。

## 產生 PDF 與 EPUB

需要 Python 3.10+、Node.js 18+ 與 XeLaTeX。Windows 可使用 MiKTeX；安裝與其他平台說明見 [電子書建置指南](docs/EXPORT.md)。

```powershell
# 首次準備：下載固定版本的工具與字型至本機 .tools/
python scripts/bootstrap_tools.py

# 書稿修改後：同時產生兩種格式
python scripts/export_book.py
```

輸出位置：

- `output/pdf/rlhf-book-zh-tw-v0.1.pdf`
- `output/epub/rlhf-book-zh-tw-v0.1.epub`
- `output/build-provenance.json`：建置 commit、內容雜湊、來源 SHA 與工具版本。

兩種格式都包含目錄、文獻與公式跳轉、來源說明及授權條款。PDF 使用內嵌正體中文字型；EPUB 使用離線 SVG 公式，不依賴閱讀器執行 JavaScript。EPUB 的字型與分頁由閱讀器決定，長公式建議使用橫向畫面或較大螢幕；公式替代文字保留 TeX，尚未提供完整的語音數學朗讀。

輸出檔、下載工具及本機協作規則不納入 Git。公開發布前，請執行指南中的自動檢查及視覺抽查。

## 內容版本

| 來源 | 記錄 |
|---|---|
| ai-twinkle 翻譯基底 | [`41834be9275d000a864e275a7347e7e13941536e`](https://github.com/ai-twinkle/rlhf-book-zh-tw/commit/41834be9275d000a864e275a7347e7e13941536e) |
| 本次沿用的增修快照 | [`9a27262290854adb9cab5515916591965600af5d`](https://github.com/YIWEI-CHEN/rlhf-book-zh-tw/commit/9a27262290854adb9cab5515916591965600af5d) |
| 原翻譯宣告的英文日期 | 2026-07-01 |
| 英文版本候選 | [`book/v0.10`](https://github.com/natolambert/rlhf-book/releases/tag/book/v0.10)，commit `854a344dc316f4c147280a3448c31cd97d953b6d`；**尚未確認與翻譯完全對應** |

以上 SHA 用於標示內容出處，不會匯入其 Git 歷史。此次整理僅搬移插圖並調整 Markdown 圖片路徑；既有正文不因重新建庫而改寫。PDF 的第一階段以這份正體中文內容為準，不宣稱已追平最新英文版。

`content/ch06.md` 是第 6 章完整內容；`ch06a.md`、`ch06b.md` 是保留的分段稿，電子書不重複收錄。章節順序與版本集中記錄於 [book.json](book.json)。

## 參與修訂

歡迎提出錯字、翻譯、公式與引用問題。請註明章節、原句，以及可核對的英文來源；翻譯修正與新版英文內容同步應分開記錄。

## 授權

書稿與翻譯沿用 **[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh-hant)**，完整條款見 [LICENSE](LICENSE)。散布增修內容時須保留原作者、翻譯社群與來源署名，說明修改，遵守非商業及相同方式分享條件。

未來匯入的程式碼保留各自原有授權、copyright 與 notices，不以書稿授權覆蓋程式碼授權。支持原作者可至 [rlhfbook.com](https://rlhfbook.com) 購買實體書。
