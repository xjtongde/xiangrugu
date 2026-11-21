# lead 锚点独立预核（2026-11-21 15:54:42 UTC，32 只读，/tmp 隔离即清）

对象：harvard-full/doi_10_7910/DVN/25413/DCW_CHINA_contours.zip!asia_contour.shp
快照 :ro zipfile 读头 100B：
- offset 24 原始字节：04 17 b8 8a
- 大端 '>i' = **68,663,434 字**（16 位字单位）×2 = **137,326,868 字节** == ZIP 成员 file_size 137,326,868 ✓（与派工锚点逐位一致）
- 小端 '<i'（缺陷读法）= -1,967,646,972 ×2 = **-3,935,293,944** == spatial_evidence.jsonl 现记录值（根因完全复现）
- shape_type offset 32 小端 = 3（PolyLine）——offset 32 按 SHP 规格本应小端，探针 L93 正确，仅 L97 offset 24 端序+单位双错。

结论：修正方案（'>i' 读 offset 24、保留字单位、×2 对账成员字节）经 lead 独立真值验证。705 件复核由 a02 执行、a03 独立重算。