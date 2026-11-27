# 首个差异（本盒实测，按发现顺序）

## D1 — 交付命令在宿主机执行，路径全属容器（a04 指出，我独立证实）
**首次出现处**：`COMMAND-FORMAL.txt` L73 / L97 的裸 `python3`。
**观测**：宿主机 `python3 -c "import xiangrugu_datamgmt"` → `ModuleNotFoundError`；
`/data/var/b-batch`、`/run/secrets` 在宿主机均不存在。
**性质**：不是"结果不对"，而是**按原文根本跑不到第二步**。静态审查看不出——
每行单独都合法，只有真去执行才暴露。与上一盒 §4-1「scope 递不进 entry」同族。

## D2 — 退出码只回显不短路（a04 指出，我用新旧对照量化）
**首次出现处**：L83 `echo "PREFLIGHT_EXIT=$?"` 之后无判断；L110 `echo "LOAD_EXIT=$?"` 收尾。
**旧形态实测**：`script_rc=0`、`preflight_exit=2`、`load_entry_called=YES`、`load_exit=77`。
**新形态实测**：`script_rc=2`、`preflight_exit=2`、`ABORT_BEFORE_LOAD`、`load_entry_called=NO`。
**危害排序**：脚本自身返回 0 比"装载被调用"更严重——它把失败伪装成成功，
上层自动化会据此继续推进到正式装载。

## D3 — 证据盒里的脚本 ≠ 交付脚本（a04 指出，我复现并修复）
**首次出现处**：容器 work 目录 `fd106f48…` vs 工作区 `916e7c07…`。
**后果**：历史 R0–R3 跑的不是交付的那份命令，其结论不能迁移到交付件上。
**修复后**：两侧同为 `0ba1c4e6…`，且本轮全部实测均以该哈希为基准。

## D4 — **本盒新发现**：`docker exec -i` 吞掉脚本正文导致永久挂起
**首次出现处**：我按 6bf26e5（已修 D1/D2）原文实跑步骤 1 的第一条探针。
**症状**：`bash -x` 追踪到 `+ docker exec -i ... python3 -c 'print(1)'` 后**无任何输出、无报错、永久阻塞**。
**根因**：`-i` 把容器 stdin 接到脚本自身 stdin。整份命令经 heredoc / `bash -s` 喂入时，
`-i` 会读走脚本尚未解析的正文，后续语句根本不存在了。
**差分证明**（同一命令体三种变体）：带 `-i` + heredoc → 挂起；去掉 `-i` → rc=0 正常；
带 `-i` 但显式 `</dev/null` → rc=0 正常。
**为何上一盒未暴露**：上一盒步骤 1/2 走的是宿主机裸 `python3`（即 D1），
从未真正执行过任何带 `-i` 的容器调用。**D1 掩盖了 D4**——修掉第一个缺陷才让第二个现形。
**规则**：`-i` 只对 (0b) 那种用 tar/cat 经 stdin 传数据的步骤必需；执行命令一律不带 `-i` 且 `</dev/null`。

## D5 — a04 第一条历史疑点：**不成立**（但我发现了相邻的真实缺口）
a04 称 manifest 读取失败会早退 `return EXIT_INPUT` 从而不写 evidence-out。
代码事实：manifest 读取在 L245，位于 L229–L270 的 try 内；其 except（L270–271）只是
`record("manifest_readable", …)` 然后**继续向下**走到 L286 写 evidence。
唯一的 `return EXIT_INPUT` 在 L187，属 scope/expected 读取。
现场复跑 R1 等价场景：exit=2、checks=12、**evidence json 写出且内含 12 条**——
与 REPRO-RECORD 记录一致，无需更正。
**相邻真实缺口**：真正跳过 evidence-out 的是 scope/expected 缺失那条路（实测 exit=4、
EVIDENCE_WRITTEN=NO）。即输入错误时不留机器可读证据。建议 preflight 在 INPUT_ERROR
分支也写一份最小 evidence。记为跟进项 F1，非本盒范围。

## D6 — a04 第二条历史疑点：**成立**，且比所指更严重
`rejections/R1-manifest-missing.out` 无 `PREFLIGHT_EXIT` 行（计数 0），
`repro/raw/R1.out` 有（计数 1）。
**额外发现**：两份件的 code_root 也不同——rejections 记 `/data/var/b-batch/code/…`，
raw 记 `code2/…`。说明 rejections/*.out **不是本轮真跑的原始输出**，而是更早一轮或改写过的快照。
REPRO-RECORD 描述的对象是 raw/ 那一份，本身没错；但目录名 `rejections/` 会让人误以为
那里存的是对应各轮的原始拒绝输出。需在记录中如实标注两者不同源。记为跟进项 F2。
