# store-perf 本机四店联调（2026-10-18）

事实来源是 Agent Store 的 `docs/local-8787-uat-20261018.md`。这里只登记那份记录，不改写结果。云端 VM 连不上桌面 `127.0.0.1:8787` 不构成这次本机联调失败。

## 锁定环境

- `STORE_PERF_BASE_URL=http://127.0.0.1:8787`
- 无服务 Token。zhilong 内网 demo 未鉴权。base URL 已配置时，空的 `CONNECTOR_STORE_PERF_API_KEY` 可以建客户端。缺 URL 仍是配置缺失。
- 机器：zhangbo-office（Windows）

| 店名 | storeId |
| --- | --- |
| LKANGYI L | 634418230343667 |
| FUDEAIB FFF | 634418230775359 |
| CHICKAN KK | 634418230611893 |
| STATXIN S | 634418230652650 |

## 本机 HTTP

全部 200：`GET /health`，`GET /data/latest`（COMPLETED），`POST /data/preload`，`POST /analysis/run`（`storeCount=4`，`abnormalStoreCount=3`），`POST /drill` 四次。

tasks 7.3 这轮不勾。勾选等双审接受这份证据之后。
