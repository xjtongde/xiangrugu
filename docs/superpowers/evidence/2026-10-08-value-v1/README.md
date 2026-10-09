# 值比较切片验证证据

本目录保存32容器执行的纯合成测试日志，不含真实源/数据库值。实施及评审结论统一见[执行账](../../plans/2026-10-08-text-value-progress.md)；设计见[规格](../../specs/2026-10-08-text-value-comparison-design.md)。

各Task和评审red/green日志记录失败原因与通过数量。最终build日志对应三个修复后候选镜像；final-verification日志记录393项、runtime smoke/pip check、dev help、镜像标签、长期容器身份及源码/夹具SHA-256。文件名及created参数不是实际执行时间，实际时间见验证日志首行。

所有.log均为新增回传证据；SHA256SUMS.txt由32生成并回传，Windows使用Get-FileHash逐件核验。不覆盖历史release，不构成源/库验收。
