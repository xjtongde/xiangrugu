# 合成清点夹具

`tests/unit/test_inventory.py` 在 pytest 临时目录生成字节明确的文件、嵌套 ZIP、重复成员、压缩炸弹、坏校验账、不可读目录和符号链接；不从真实 usedata 复制样本。生成式夹具便于在 Linux 非 root 容器检验权限，且不会在仓库保存危险归档或依赖 Windows 的链接权限。
