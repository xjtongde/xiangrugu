# 第五盒：按交付命令原样跑通 + 分开导出与核哈希

## 核心缺陷（已修，`e792f1e`）
L65 的清单条目检查用 `os.environ['CODE_ROOT']`，但那条 `docker exec` **没有传 `-e CODE_ROOT`**。
容器内取不到该变量 → `KeyError: 'CODE_ROOT'`，实测 **exit 1**：按交付命令原样执行步骤 0 必然失败。
此前几轮能过，是因为我手工补了环境变量——正是本盒明令禁止的做法。

**选择位置参数而非 `-e CODE_ROOT=…`，理由**（已写进注释）：与本块上方 0c-1/0c-2 的
`sh -c '…' sh "$X"` 形态一致；被测值显式出现在命令行上，读命令即知用了什么值，
不依赖调用环境恰好存在同名变量——那种隐式依赖正是本缺陷的来源。
修后审计：文件内已无 `os.environ` 引用，其余容器内片段均走 `"$1"` 位置参数。

## 分开导出（本盒新增要求）
| 来源提交 | 内容 | 落地位置 |
|---|---|---|
| `a5d12b1`（固定运行时） | runner 运行时 + 16 模块 | `/data/var/b-batch/code5/xrg-batch`（`git archive` 全新解包） |
| `e792f1e`（交付提交） | 正式命令、预检脚本、输入工件 | `/data/var/b-batch/work5`（另一 tar，不与运行时混装） |

16 模块清单 `PIN_MODULES.json` 是独立交付件，安装到运行时树根 `$CODE_ROOT/PIN_MODULES.json`。

## 两个位置必须写清（本盒要求）
1. **实际执行的 `preflight.py`**：`/data/var/b-batch/work5/.b-batch-real-runner-binding-20261127/preflight.py`
   = `8be2202bab84…` = 交付提交 `e792f1e` 的 blob。**不是** code5 里那份旧的 `63f2738a…`。
2. **实际 `import xiangrugu_datamgmt` 解析到**：`/data/var/b-batch/code5/xrg-batch/datamgmt/src/xiangrugu_datamgmt/__init__.py`
   = a5d12b1 导出树。**不是** site-packages，也不是 `/workspace` 的 deploy 树。
   （容器 env 自带 `PYTHONPATH=/workspace/datamgmt/src`，靠 `-e PYTHONPATH="$CODE_ROOT/datamgmt/src"` 覆盖掉。）

## 原样跑通的输出
```
=== 步骤 0 ===
PIN_COMMIT_OK=a5d12b13ad87b74fea5e8e7b2fb8a2c901bbad9e
REGULAR_FILE_OK
PIN_MODULES entries = 16
STEP0_PROBE_EXIT=0 module=/data/var/b-batch/code5/xrg-batch/datamgmt/src/xiangrugu_datamgmt/__init__.py
STEP0_ALL_PASS rc=0
STEP0_SCRIPT_RC=0

=== 步骤 1 ===
PROBE_RC=0（同上，解析到导出树）
{"outcome": "PASSED", "failure": null, "checks": 17}
PREFLIGHT_EXIT=0
STEP1_OK_CONTINUED
STEP1_SCRIPT_RC=0
```
未手工补任何环境变量；干净目录 code5/work5 由 `rm -rf` + 全新解包得到。

## 正负对照（marker 一律容器内判读）
```
POSITIVE  正确 PIN + 真实载荷 : PASSED checks=17 PREFLIGHT_EXIT=0 → LOAD_ENTRY_CALLED=YES  LOAD_EXIT=77 SCRIPT_RC=77
NEGATIVE A 错误 PIN           : FAILED rc=2 → ABORT_BEFORE_LOAD   LOAD_ENTRY_CALLED=NO   SCRIPT_RC=2
NEGATIVE B 坏载荷身份         : FAILED rc=2 → ABORT_BEFORE_LOAD   LOAD_ENTRY_CALLED=NO   SCRIPT_RC=2
                              detail: bytes=1 want 417981;lines=1 want 3859;sha256=2d711642… want 5ca84bdc…
```
**反例纪律已遵守**：NEGATIVE B 用**新建独立文件** `payload-box5-1byte.bin`，
未对 `payload.bin` 做任何重定向；跑前跑后都回读确认 `payload.bin untouched: 417981`。
退出码全部 `RC=$?` 紧跟命令取，无管道。

## 🔴 本盒新发现的自身操作隐患（值得入纪律）
上一盒我用 `docker cp … xiangrugu-dev:/data/var/b-batch/payload.bin` 把载荷送进了容器。
本轮排查发现：**宿主 32 上另有一个互不相干的 `/data/var`**（`drwxr-xr-x root root`，
建于 00:13，里面只有我自己误建的 `b-batch-real/`）。容器的 `/data/var` 是
`/opt/mydocker/xiangrugu/data/var` 的 bind mount，两者路径字符串相同但命名空间不同。

后果有两层：
1. 我在宿主 shell 里直接引用 `/data/var/...` 会落到那个无关目录，报
   `lstat /data/var/b-batch: no such file or directory`——本轮步骤 0 第一次就是这么失败的。
2. 更危险的是 `test -f /data/var/b-batch/payload.bin` 这类**核验**若在宿主侧做，
   验的根本不是容器里那份。这与上盒 marker 假阴性同构：**跨命名空间的路径字符串看起来一样，
   于是校验静默地作用在错误对象上**。

处置：宿主侧一律用挂载真源 `/opt/mydocker/xiangrugu/data/var/b-batch/...`；
凡"这个文件对不对"的断言都在容器内做。本次载荷本身无恙——两侧副本 sha256 均为
`5ca84bdc…`，容器内那份可读且被 `mode=ro` 正常消费。

## 逐件摘要
运行时树 16 模块 vs 清单：**16 MATCH / mismatch 0**（明细见 DIGESTS.txt）。
交付侧工件与 git blob 逐一相等：
```
COMMAND-FORMAL.txt              d6d93b602fb9  = e792f1e blob ✅
preflight.py                    8be2202bab84  = e792f1e blob ✅
formal-scope.json               655bd3382c3d
formal-expected.json            43f7705fd0bf
approval-text-verbatim.txt      4d250c8e08ea  = 批准授权文本 ✅
b-approval-table-v2.json        a718b0c29750  = 批准表 ✅
b-single-table-frozen-candidate 5281cfcedfe1  = 冻结候选 canonical 文件 ✅
PIN_MODULES.json                e6a1ac6ceb9a  = 交付清单 ✅
payload.bin                     417981 B / 5ca84bdc9bb4 ✅
```
