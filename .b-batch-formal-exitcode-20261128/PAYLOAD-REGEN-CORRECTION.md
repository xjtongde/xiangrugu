# 更正：重生成路径的记录不实，以及真实原因

## 我写错了什么
`PAYLOAD-IDENTITY-FIX.json.why_no_pydantic_import` 写的是：
> 宿主 32 无 pydantic，故未 import xiangrugu_datamgmt……这使重生成的校验强度低于包内路径。

前半句对（32 上 `python3 -c "import pydantic"` → ModuleNotFoundError），**后半句推论错**。
复核人实测并成立，我也复验：容器内 `pydantic 2.13.5` 存在，
`import xiangrugu_datamgmt` → `/workspace/datamgmt/src/xiangrugu_datamgmt/__init__.py` 可导入。
我把「宿主机无 pydantic」错误推广成「无法用包内路径」，据此放弃了一条本来可用的更强路径。

## 真实原因（比我的解释更难看，也更该记下来）
我第一次在容器内跑包内路径时确实失败了，报 `SQLiteValueReadError: unsafe_path`。
我当时把它读成"包内路径不可用"，于是退回宿主机自造校验。**实际上失败是我自己的脚本 bug**：

```python
SNAP = "/data/imports/2026-10-07-bootstrap/harvard/cbdb/cbdb_20260919.sqlite3"   # 我凭空假设的挂载点
```
容器内该路径 `exists: False`。`_checked_stat` 的 `except OSError → unsafe_path`
把"文件不存在"和"路径不安全"**合并成同一个错误码**，所以一个拼错的路径看起来像是安全策略拒绝。
隔离实验证实：同一份调用，正确路径 `rows 3859`；错误路径 `RAISED unsafe_path`。

同一段脚本里还有第二个 bug：`stream.summary` 在 `with` 块外访问（缩进错了一级）。
两处都是我的问题，与容器能力无关。

## 已按包内路径重做（两条都跑）
| 运行位置 | PYTHONPATH 解析到的包 | rows | bytes | sha256 |
|---|---|---|---|---|
| dev 容器（deploy 树） | `/workspace/datamgmt/src/…` | 3859 | 417981 | `5ca84bdc9bb4…` |
| dev 容器（固定导出树 a5d12b1） | `/data/var/b-batch/code3/xrg-batch/datamgmt/src/…` | 3859 | 417981 | `5ca84bdc9bb4…` |

源件通过硬链接暴露给容器：`ln` 引导清单已核验的副本到 `/data/var/b-batch-src/`，
**inode 相同（1337005）、链接数 2、未复制 586 MB 数据**；两份源副本 sha256 同为
`bde1bb8e…`、size 同为 586485760。三份产物 `cmp` 全部 `ALL_IDENTICAL`：
`payload.bin` / `payload.inpkg.bin` / `payload.inpkg-export.bin`。
包内路径预检：`PASSED checks=17 PREFLIGHT_EXIT=0`。

结论：**内容从未出错，但证据链的生成路径此前确实弱于要求**。现已补齐，根上不留缺口。

## 关于"是否值得重做"——我支持重做，并已做
反对理由（摘要相同即内容相同）技术上成立，但它保护的是**结论**而不是**论证方式**。
本项目核心条款是"验收结论由机器可读证据支持"，而载荷是所有后续证据的根；
如果根是用一条我自己承认更弱的临时路径产出的，那么后续每一层都在继承这个折扣。
成本是一条命令，收益是链条闭合——这笔账明显偏向重做。

## 第五条：源件身份，给出可独立重算的形式
我之前只说"读前后身份不变"却没留可复核的数据。补上权威源当前值：
```
size=586485760  mtime=1790061161  inode=78251187
sha256=bde1bb8eece3820d9e236c1d6b0f07d847d339669d4a85d79cd7252d58d83400
```
任何人可在 32 上用 `stat -c "size=%s mtime=%Y inode=%i"` + `sha256sum` 重算比对。
注：mtime 是源件自身的历史时间戳，不是本次读取时间；本次读取以 `mode=ro` URI 打开，
且包内 `_read` 在流结束后自行做了 `_identity(before) != _identity(after)` 与终哈希比对。

## 教训（建议进纪律）
1. **不要把"我以为环境没有 X"写成记录里的理由。** 一句 `docker exec … python3 -c "import pydantic"` 就能否掉我的说法——我没做这个验证就下了结论，这才是真正的失误，比选错路径更严重。
2. **`unsafe_path` 这类合并错误码要拆开验证。** 遇到"安全策略拒绝"先单独测 `os.path.exists()`，区分"不存在"与"不安全"，否则会把自己的笔误当成约束条件并接受降级方案。
