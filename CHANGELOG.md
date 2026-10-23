# CHANGELOG

## [Unreleased]

### 新增
- `tools/sparks_diff.py`：以 sparks.bible 經文內嵌的專名標籤（USFM pn）為參照，整卷／全本批次比對，列出我們漏標的詞與疑似誤標的詞。僅作人工審核的參照，不複製對方內容。報告含每個詞的書卷分布（單卷／多卷），`--out` 可把完整報告寫入檔案以節省對話 token。
