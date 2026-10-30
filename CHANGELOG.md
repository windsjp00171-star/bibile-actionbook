# CHANGELOG

## [Unreleased]

### Changed
- 讀經頁的內嵌 JavaScript（約 1000 行）拆成 `static/js/read-*.js` 九個檔案，功能不變；靜態檔網址加上版本參數，避免已安裝的 PWA 沿用舊版 JS
- 教學導覽改用 `data-tour` 屬性綁定目標元素（讀經頁 14 處、搜尋頁 3 處），不再依賴 id／class，導覽行為與步驟不變

### Added
- 新增 `PRODUCT.md`，記錄產品定位、受眾與長者友善的適用範圍（讀經頁為準、首頁入口較自由）
- 新增 `DESIGN.md` 與 `.impeccable/design.json`，記錄改版前的視覺系統現況（含首頁進入動畫與待重構問題），作為重構基準
