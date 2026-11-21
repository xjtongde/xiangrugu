# 世界文件文本出处定点更正 · lead 锚点预核（2026-11-21，10 分钟盒）
- 起表 17:02:33 UTC，硬停 17:12:33 UTC。基线 c2ef3ca64ea6f4f83a02484b634b13486ce3e8c3（M=2 完好、暂存空）。
- 缺陷确证（lead 38 实测）：交付 raster-mapping 1926_01.jgw text_provenance.verbatim CRLF=0（LF）。
- 回归锚点（lead 32 只读独立实测，17:03:09 UTC）：harvard-full/doi_10_7910/DVN/23340/1926_China_Atlas.zip!1926_01.jgw[39] 原件 120 B，**CRLF=6 / LF=6**，sha256 f070b7935f68389f…==inventory 声明；repr 头 b'3072.9925610571327\r\n-274.3726354288097\r\n…'。
- 结论：probe 转录时换行已规整（CRLF→LF），「verbatim/源成员字节转录」声明不实；更正方向=探测文本（换行及末尾空白已规整）+规整文本（六浮点重序列化）双标注，原件以 source_member+SHA-256 定位。
