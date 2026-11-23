# 涨潮断面通行簿深度登记

- 中型。用精确阈值交点及航行偏移求全程潮窗。

## 功能模块

| 模块 | 使用者动作 | 入口 | 核心文件 | 测试 |
|---|---|---|---|---|
| M1 潮尺读数采信 | 查重复刊头和隔离行 | `/api/stage/readings` | `app/modules/intake/readings.py` `app/modules/intake/service.py` | `tests/test_readings.py` |
| M2 站点基准统一 | 复核孪站裁决 | `/api/stage/datum` | `app/modules/datum/resolve.py` | `tests/test_datum.py` |
| M3 水位阈值交点 | 查看来源点和交点 | `/api/stage/crossings` | `app/modules/crossings/interpolate.py` | `tests/test_crossings.py` |
| M4 全程可行潮窗 | 查断面偏移后的区间 | `/api/stage/windows` | `app/modules/passage/service.py` `app/modules/passage/state.py` | `tests/test_windows.py` |
| M5 船期覆盖勾稽 | 回查申请时点和时长差额 | `/api/stage/coverage` | `app/modules/schedule/service.py` | `tests/test_coverage.py` |
| M5b 往返成对时刻 | 按卸货时长重算两程、确认往返安排 | `/api/roundtrip/<vessel>` | `app/modules/roundtrip/service.py` `app/modules/roundtrip/confirm.py` | `tests/test_roundtrip.py` `tests/test_roundtrip_api.py` |
| M6 批次留档复跑 | 同源复算及归档查阅 | `/api/journal` | `app/modules/journal/service.py` `app/modules/journal/store.py` | `tests/test_journal.py` |
| M7 潮窗证据签发 | 验证原件及报告摘要 | `/api/export/<id>` | `app/modules/proof/service.py` | `tests/test_proof.py` |

| TRAP | 现象 | 朴素处理后果 | 处理 | 位置 | 测试 |
|---|---|---|---|---|---|
| TRAP-02 | 潮尺 BOM | 站号列错认 | 消除开头 BOM | `app/modules/intake/readings.py` | `tests/test_readings.py::test_bom` |
| TRAP-04 | 分段重复表头 | 表头当读数 | 记录分段并跳过 | `app/modules/intake/readings.py` | `tests/test_readings.py::test_repeated_header` |
| TRAP-05 | 多余列 | 原件错位 | 隔离留原列数组 | `app/modules/intake/readings.py` | `tests/test_readings.py::test_wrong_width` |
| TRAP-07 | 潮尺 N/A | 以零插值 | 隔离并保留原值 | `app/modules/intake/service.py` | `tests/test_readings.py::test_sentinel` |
| TRAP-10 | 三分之一秒交点 | 临界比较漂移 | 有理数插值 | `app/modules/crossings/interpolate.py` | `tests/test_crossings.py::test_exact_fraction` |
| TRAP-11 | Z 与东八区同刻 | 重复时间点 | 统一 UTC 秒 | `app/clock.py` | `tests/test_datum.py::test_timezone_repeat` |
| TRAP-14 | 同时潮尺矛盾 | 后报覆盖 | 同键冲突全部隔离 | `app/modules/datum/resolve.py` | `tests/test_datum.py::test_conflicting_station` |
| TRAP-15 | 厘米、米混用 | 水深错档 | 按单位换算后加基准 | `app/modules/datum/resolve.py` | `tests/test_datum.py::test_normalize_unit` |
| TRAP-19 | 孪站同刻 | 顺序决定选站 | 显式优先级 | `app/modules/datum/resolve.py` | `tests/test_datum.py::test_station_priority` |
| TRAP-23 | 船期右端 | 重复归属 | 排除右端 | `app/modules/passage/service.py` | `tests/test_windows.py::test_half_open_end` |

海棠17窗口 3000 秒 = 1500 可行 + 900 不可行 + 600 缺证。潮尺接收 20 条数据，18 条格式采信，11 条进入断面判定，2 条格式隔离、7 条业务隔离。重复表头及空行单计。以分钟级实测样例演示，不覆盖未带偏移的当地时刻、曲线外推和实时设备连接。

## 往返配对规则（M5b）

- 船期页按当前卸货时长 `unloading_s` 同时给两套成对出发时刻：`early` 早走腾位（去程取船期内最早可行时刻，回程取卸货就绪后的最早可行时刻）、`late` 晚走留余（从最晚可行槽位倒推，仍须赶上回程窗）；两程时刻完全相同时只保留一份。
- 回程出发必须满足 `回程出发 ≥ 去程出发 + 卸货时长`，且严格落在船期右端之前（沿用 `[start,end)` 半开语义）。卸货时长一改，两程时刻整体重算。
- 船期内无去程窗记 `NO_OUTBOUND_WINDOW`；卸货后找不到回程窗记 `NO_RETURN_WINDOW`，往返不成立、不确认。
- 确认写 `roundtrips` 表，主键 `(run_id, vessel)`：两人同时提交不同安排时数据库只接受一份，另一方收 `SCHEDULE_TAKEN` 409。
- 重试同一安排（同原件、同船、同卸货时长、同两程时刻）命中确定性 `plan_key`，返回 200 且不重复留档。
- 留档明细逐断面保存去程、回程各自的潮尺行（`lines`）、插值水深和判定码，可在 `/api/journal/<id>/roundtrips` 回查。
