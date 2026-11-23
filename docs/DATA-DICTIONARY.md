# 潮窗数据字典

| 原件 | 字段 | 定义 |
|---|---|---|
| observations.csv | station, observed_at, level, unit, quality | 文本站号、带偏移整秒、潮尺小数、m/cm/mm、OK/BAD |
| stations.csv | station, section, datum_m, bed_m, priority, offset_s, gap_s | 测站及断面、基准和河床高程、正整数优先级、过断面时间偏移、允许插值的最大观测间隔 |
| vessels.csv | vessel, draft_m, clearance_m, start, end, requested | 船期键、吃水和富余、出发时窗及申请时刻 |

CSV 接受 UTF-8 BOM 和任意字段排列。输入必须有全部字段，空串及 `-`、`N/A`、`NULL`、`未知` 进入逐行隔离。纯空文件、空行文件和仅表头分别报告。单份自带 UTF-8 文本上限 256 KB。结构性有误的测站或船期表中止计算，观测坏行保留原件与行号。

水深 = 潮尺读数换算到米 + 站点基准 − 河床高程。水位使用精确有理数，JSON 以分数字符串保留精度。输出时刻以 UTC Unix 秒表示，插值交点可为分数秒。相邻有效读数之间仅在间隔未超过 `gap_s` 时插值，读数本身可作为独立时点证据，不向时窗两头外推。

同站同刻、同水深保留最早原始行。冲突水深隔离全部冲突行。优先级数值小的站优先；同优先级矛盾时保留冲突，若一致按站号排序。船期 `[start,end)`，断面达标包含恰等瞬时。跨日连续求交不按自然日截断。已知低水位足以驳回，其余情况只要有缺证即缺证。持续时间按互斥区间累计，单点计 0 秒。

归档以规则版本、原件 SHA-256 定址。导出附原件、阶段结果、运行参数和摘要。验签用于检出内容变化，摘要没有第三方身份签名含义。

## 往返安排接口

| 接口 | 方法 | 说明 |
|---|---|---|
| `/api/roundtrip/<vessel>` | GET | 预览成对时刻；参数 `unloading_s`（非负整数秒，默认 900）、`sample` 或 `sources`，带 `run` 时读留档并回附确认状态 |
| `/api/roundtrip/<vessel>` | POST | 确认往返；体含 `plan`（`early`/`late`）与卸货时长，成功 201，同安排重试 200，异安排冲突 409，回程无窗 422 |
| `/api/journal/<id>/roundtrips` | GET | 列出该运行簿下各船期已确认的往返安排 |

`pairing.plans` 每个方案含 `outbound` 与 `return_leg` 两条腿，各自给出 `departure`（UTC Unix 秒，可为分数秒字符串）、断面 `evidence`（水深、判定码、潮尺原始行号 `lines`），以及 `unload_ready`（去程出发加卸货时长）和 `buffer_s`（回程出发相对卸货就绪的富余秒）。确认指纹 `plan_key` 由运行簿、船期、卸货时长和两程出发时刻规范哈希得到；`roundtrips` 表以 `(run_id, vessel)` 为主键，保证同一船期只有一份确认。
