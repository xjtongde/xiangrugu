# -*- coding: utf-8 -*-
"""datamgmt/db.py —— pg32b 唯一通道：ssh → docker exec → psql。

定位：这是"驱动器"层（等价于 psycopg2 之于本地库），load.py 与 verify.py 皆用；
　业务代码（读取/解码/真值/比对）零共用，仍守 §6.1 独立性铁律。

关键点：
* SQL 与 COPY 数据一律经 **stdin** 送 psql——绝不经远端 shell，故无引号注入之虞；
  唯一经 shell 的是 psql 命令行旗标，且由本文件固定写死（-F'|' 已 quote）。
* 出错即抛（ON_ERROR_STOP=1，非零返回/错误文本一律 raise）。
"""
import subprocess

HOST = "192.168.3.32"
CONTAINER = "pg32b"
USER = "postgres"


def _ssh_exec(remote_cmd, stdin_data=b""):
    p = subprocess.run(["ssh", HOST, remote_cmd],
                       input=stdin_data, capture_output=True)
    out = p.stdout.decode("utf-8", "replace")
    err = p.stderr.decode("utf-8", "replace")
    return out, err, p.returncode


def _raise_if_error(out, err, rc, context):
    if rc != 0 or "ERROR" in out or "ERROR" in err:
        raise RuntimeError(f"[db] {context} rc={rc}\n--- stdout ---\n{out}\n--- stderr ---\n{err}")


def query(db, sql):
    """运行 SQL（经 stdin），返回 (stdout, stderr, rc)。stdout 为 -At -F'|' 分隔文本。"""
    remote = f"docker exec -i {CONTAINER} psql -U {USER} -d {db} -v ON_ERROR_STOP=1 -At -F'|'"
    return _ssh_exec(remote, sql.encode("utf-8"))


def execute(db, sql):
    """运行 DDL/无关结果之 SQL，出错即抛。"""
    out, err, rc = query(db, sql)
    _raise_if_error(out, err, rc, context=sql[:80])
    return out


def rows(db, sql):
    """query 的解析版：返回 list[list[str]]。剥掉 psql 输出末尾换行伪行。"""
    out, err, rc = query(db, sql)
    _raise_if_error(out, err, rc, context=sql[:80])
    if not out.strip():
        return []
    out = out.rstrip("\n")   # psql -At 每行一换行，末行后有多余 \n
    return [ln.split("|") for ln in out.split("\n")]


def copy_to(db, sql):
    """COPY … TO STDOUT：返回原始 stdout（csv 文本，可含 | 与换行——皆由 csv 引号包住）。"""
    out, err, rc = query(db, sql)
    _raise_if_error(out, err, rc, context=sql[:80])
    return out


def copy_stream(db, copy_sql, csv_text):
    """COPY ... FROM STDIN；csv_text 紧跟其后，以 \\. 收尾（全经 stdin）。"""
    payload = copy_sql.rstrip("\n") + "\n" + csv_text
    if not payload.endswith("\n"):
        payload += "\n"
    payload += "\\.\n"
    remote = f"docker exec -i {CONTAINER} psql -U {USER} -d {db} -v ON_ERROR_STOP=1"
    out, err, rc = _ssh_exec(remote, payload.encode("utf-8"))
    _raise_if_error(out, err, rc, context=copy_sql[:120])
    return out


def quote_ident(name):
    """标识符定界：一律双引号包裹（表名/列名可能含数字开头/保留字）。"""
    return '"' + name.replace('"', '""') + '"'


SCHEMAS = ["chgis", "harv"]


def ensure_schemas(db):
    for s in SCHEMAS:
        execute(db, f"CREATE SCHEMA IF NOT EXISTS {quote_ident(s)};")


if __name__ == "__main__":
    import sys
    db = sys.argv[1] if len(sys.argv) > 1 else "cbdb_reh"
    for r in rows(db, "select 'ok', current_database(), count(*) from pg_database;"):
        print(r)