# Octop：Harness MCP 与 Skills 注入深挖

只读核对。产品代码未改。标识符保持英文。

核对范围：本仓库工作区源码，加上 lock 里的依赖源码（只读解包，未安装进环境）：

| 包 | 版本 | 来源 |
| --- | --- | --- |
| 本仓库 | `main` 工作区 | `src/octop/`、`dashboard/src/` |
| `octop-harness` | `1.0.1` | `uv.lock` wheel `octop_harness-1.0.1-py3-none-any.whl` |
| `octop-gateway` | `1.0.0` | `uv.lock` wheel `octop_gateway-1.0.0-py3-none-any.whl` |

`deepagents` 的 `SkillsMiddleware` 如何逐字节扫描 `SKILL.md` 不在本次解包范围内。Octop / harness 把目录根交给它，过滤发生在 `SkillFilterMiddleware`。

---

## 1. 结论

1. **MCP 工具不是“开了连接器就每回合都在”。** 启动时只登记配置。真正出现在模型工具列表里，要同时满足：工具已挂到运行中的 `HarnessAgent`，并且本回合 `ChatRequest.mcp_servers` 点名了对应 server。没点名时 `MCPToolMiddleware` 把全部 MCP 工具剥掉。
2. **`default_open` 与 Dashboard 回合列表是两条规则。** Dashboard WebSocket 只要带了 `mcp_servers`（含 `[]`），服务端 `apply_defaults=False`，不再并上 `default_open`，也不并上专家行上的 `agents.mcp_servers`。缺这个键才走 IM 式默认合并。Dashboard UI 会在新会话里预先勾上 `default_open ∪ expert.mcp_servers`，然后把结果当作显式数组发出去。
3. **custom-mcp 与 catalog 连接器加载时机不同。** Catalog 里带 `transport` 的 remote / internal 在 agent 启动时 `aload_mcp_tools`。`mcp_mode=gateway` 是进程内注入，不走 HTTP preload。`custom-mcp` 在启动配置里写成没有 `transport` 的 `{}`，harness 跳过加载；工具在 `prepare_chat_mcp` 里按用户缓存 `aload`，再 `append_mcp_tools`。
4. **没有 `/skills/.../reload`。** 启用 / 禁用只写 `skills_disabled` 并 `HarnessAgent.set_skills_disabled`。该方法不重编译图。`AgentManager.reload` 是整实例 `arebuild_agent`，技能开关不走它。
5. **当前 Dashboard 聊天帧不发送 `skills`。** 输入框里的 skill token 只进本地气泡的 composer context。服务端因此看不到 `request["skills"]`，`SkillFilterMiddleware` 放行全部已启用 skill。`/slug` 只是写进 system prompt 的阅读约定，不是服务端 allow-list。
6. **`ask` / `plan` 会在请求上把 skills 和 MCP 都清空。** Dashboard 还会先把 connectors 发成 `[]`。两边都会发生。

---

## 2. MCP：builder、`prepare_chat_mcp`、`default_open`

### 2.1 启动时谁写出 `mcp_server_configs`

`AgentManager._build_harness_config`（`src/octop/infra/agents/manager.py:3068`）在非 team host 上调用 `build_mcp_server_configs_for_user`（`src/octop/infra/connectors/builder.py:505`）。

Catalog 实例来自 `connector_repo.list_visible`，`status == "active"`，且 `get_catalog_entry(kind)` 有条目：

| `mcp_mode` | 启动时写入的 spec | 工具从哪来 |
| --- | --- | --- |
| `gateway`（`is_inprocess_gateway`，`catalog.py:81`） | `{}`，没有 `transport` | `inject_missing_gateway_tools`（`builder.py:598`）。`_post_start_agent`（`manager.py:2624`）和 `prepare_chat_mcp._attach_gateway_tools`（`manager.py:1851`）都会调 |
| `internal` | `build_http_mcp_spec` → `_build_gateway_spec`（`builder.py:210`），`transport=http`，URL 是 `/api/internal/mcp/{kind}/{instance_id}` | harness 启动 `aload_mcp_tools`。spec 无 `transport` 会被跳过（`octop_harness/mcp.py` `_connection_spec_loadable`） |
| `remote` | `_build_remote_spec`，带 `transport` + URL / headers | 同上，启动时 `aload` |

Server 名：`mcp_server_name(kind, instance_id)` = `{kind}__{instance_id}`（`builder.py:58`）。

`custom-mcp`（`CUSTOM_MCP_KIND = "custom-mcp"`，`src/octop/infra/connectors/custom_mcp.py:16`）不是 catalog 条目。`ConnectorService.custom_harness_configs`（`service.py:584`）用 `enabled_harness_configs` 抽出 langchain-mcp-adapters 字段。`build_mcp_server_configs_for_user` 故意不把这份 spec 交给启动加载：

```560:564:src/octop/infra/connectors/builder.py
    custom_configs = svc.custom_harness_configs(user_id)
    for name, spec in custom_configs.items():
        # Defer loading: placeholder without ``transport`` so harness skips
        # aload at agent start. Tools are injected via prepare_chat_mcp + cache.
        configs[name] = {}
```

名字是用户起的 server 名，不是 `{kind}__{id}`。共享实例会改成 `shared_mcp_server_name(parent.instance_id, name)`。

Team host 在 `_apply_team_host_config`（`manager.py:3476`）里把 `mcp_server_configs` 和 `skills_dir` 清空。`prepare_chat_mcp` 对 team 直接返回 `[]`（`manager.py:1687`）。

启动后 `_post_start_agent` 只补 gateway 进程内工具，不加载 custom-mcp。

### 2.2 `prepare_chat_mcp` 决策

`AgentManager.prepare_chat_mcp`（`manager.py:1669`）。入参是已经合并好的 server 名列表。返回值是**仍然没有已加载工具**的名字；空列表表示这些名字都就绪。

判定“已就绪”：`agent._mcp_tool_name_set` 里有任意工具名以 `{server}_` 开头（harness `tool_name_prefix=True`）。

分支：

1. 没有 missing → 返回 `[]`，不碰 `reload_connectors`。
2. 名字在 `custom_harness_configs` 里 → `_get_or_load_mcp_tools`（用户 + server + spec fingerprint 缓存，`manager.py:1571`）→ `agent.append_mcp_tools` → 把完整 spec 写回 `agent.config.mcp_server_configs[name]`。**不**调用 `reload_connectors`。单测 `tests/unit/agents/test_mcp_tool_cache.py` `test_prepare_chat_mcp_injects_custom_from_cache`。
3. 名字在 `gateway_mcp_server_names` 里 → `_attach_gateway_tools`：刷新凭证，`inject_missing_gateway_tools`。**不** `reload_connectors`。单测 `test_prepare_chat_mcp_attaches_gateway_tools_without_reload`。注释写明：整实例重建会关掉正在写 checkpoint 的 pool。
4. 其余 builtin（remote / internal，spec 里本来就有 `transport`）→ `reload_connectors`（整实例重建）→ 若工具仍缺，对仍带 `transport` 的子集再 `aload_mcp_tools` + `append_mcp_tools`。
5. 第 4 步的整实例重建会丢掉此前 `append` 的 custom 工具。同一函数末尾按缓存再注入一次（`manager.py:1814`）。

`append_mcp_tools`（harness `agent.py`）会 `_init_graph()`。所以“不 reload”指的是不走 `AgentManager._reload_agent` / `arebuild_agent`，图仍然会重编译。`MCPToolMiddleware` 在 `_build_middleware`（harness `agent.py:1471`）里把当时的 `mcp_server_configs` 键和 `_mcp_tool_name_set` **快照**进中间件。custom 路径是先 `append_mcp_tools`（此时占位 `{}` 已在 configs 里，名字能进快照），再把带 `transport` 的 spec 写回去。保存 custom-mcp 会先 `reload_connectors_for_user`，重建后的配置里已经有占位名，下一回合的 append 才能被中间件认作已知 server。

### 2.3 `reload_connectors` 什么时候发生

| 调用点 | 行为 |
| --- | --- |
| `AgentManager.reload_connectors`（`manager.py:1479`） | team host 或无法解析 user id 则返回。对其余 active 实例 `ensure_fresh_credentials`，然后 `_reload_agent` |
| `reload_connectors_for_user`（`manager.py:1509`） | 先 `invalidate_mcp_tool_cache(user_id)`，再对该用户的 agent 以及 `user_id IS NULL` 的共享 agent 调 `reload_connectors` |
| `api/routers/connectors.py` `_schedule_connector_reload`（`:454`） | 后台任务。`PUT /connectors/custom-mcp`、patch、catalog 创建/更新/删除都会调度。`shared=True` 时 `reload_all` |
| `prepare_chat_mcp` | 仅 builtin missing（非 custom、非 gateway） |

`AgentManager.reload`（`manager.py:1376`）就是 `_reload_agent`：`arebuild_agent` + `_post_start_agent`。它给插件安装、provider 变更、连接器刷新用，不给 skill enable 用。

### 2.4 `default_open` 与回合 `mcp_servers`

合并实现：

- `ConnectorService.list_default_open_mcp_server_names`（`service.py:531`）：catalog 行要 `status=active`、有凭证、`config_json.default_open is True`；custom spec 要 `enabled` 且 `default_open is True`。
- `ConnectorService.merge_turn_mcp_servers`（`service.py:548`）：先收集 `default_open`，再把 `extra_defaults` 里仍出现在 `list_active_mcp_server_names` 的名字并进去。
- `merge_mcp_servers_with_defaults`（`src/octop/infra/connectors/default_open.py:36`）：
  - `apply_defaults=True`：显式列表与 defaults 求并集。
  - `apply_defaults=False`：只信显式列表。`[]` 得到 `None`（调用方不再注入）。
  - `apply_defaults=None`：仅当 `explicit is None` 时应用 defaults。
- `extra_defaults` 来自 `AgentManager.default_mcp_servers`（`manager.py:1653`），即 agent 行的 `mcp_servers`（专家 composer 默认），不是连接器上的 `default_open`。

`GlobalProcessor._resolve_turn_mcp_servers`（`processor.py:1545`）把合并结果交给 `prepare_chat_mcp`。失败且 `raise_on_failure=True`（Dashboard / HTTP）抛 `ErrorCode.CONNECTOR_MCP_LOAD_FAILED`。IM 传 `raise_on_failure=False`，失败则本回合跳过 MCP，不中断消息（`processor.py:769`）。

`_build_dashboard_request`（`processor.py:1341`）：

```1341:1348:src/octop/infra/gateway/process/processor.py
        explicit_mcp = meta.get("mcp_servers")
        # Dashboard always sends mcp_servers (possibly []); trust that list so
        # users can opt out of default_open for a turn. Missing key → IM-style defaults.
        if isinstance(explicit_mcp, list):
            apply_defaults = False
        else:
            explicit_mcp = None
            apply_defaults = True
```

`build_dashboard_inbound`（`turn.py:321`）在 `prepared.mcp_servers is not None` 时写入 metadata，**包括 `[]`**。`validate_chat_mcp_servers`（`api/common/validators.py:36`）对 `None` 返回 `None`，对 `[]` 返回 `[]`，非空则必须落在该用户 `list_active_mcp_server_names` 里。

因此：

| 入站 | `apply_defaults` | 实际注入 |
| --- | --- | --- |
| Dashboard 帧带 `mcp_servers: ["qq-mail__…"]` | `False` | 只这些名字（先在 `prepare_dashboard_turn` 里 `prepare_chat_mcp`，worker 里再走一遍） |
| Dashboard 帧带 `mcp_servers: []` | `False` | 不注入。单测 `test_dashboard_request_trusts_explicit_opt_out` |
| 帧里没有该键（IM、或未带字段的客户端） | `True` | `default_open` ∪ 仍可用的 `agent.mcp_servers`。单测 `test_im_call_merges_default_open_mcp_servers` |
| Cron 任务自己有 picks | `False`（`cron/delivery.py:191`） | 只信任务列表 |
| Cron 任务 picks 为空 | `True`（`delivery.py:201`） | 同 IM |
| Team host | 不合并 | `mcp_servers` 不出现在 request 上 |

Dashboard 客户端在新会话里用 `resolveInitialConnectors`（`dashboard/src/pages/Chat/utils/resolveInitialConnectors.ts`）预选。defaults 是 `withDefaultOpenKnowledgeBases(default_open 的 mcp_server_name, expert.mcp_servers)`（`useChatComposerResources.ts:235`）。这个并集发生在浏览器里，然后 `sendTurnWebSocket` **总是**把数组放进帧（`chatStore.ts:2577`）。服务端看到的是显式列表，不会再做一次 `default_open` 合并。用户把 chip 清掉后发出 `[]`，服务端不会把 `default_open` 加回来。

Harness 侧：`ChatRequest.to_runnable_config`（`octop_harness/request.py:110`）把 `mcp_servers` 抄进 `configurable`。`MCPToolMiddleware`（`octop_harness/middleware/mcp_tools.py`）在 `mcp_servers` 与 `mcp_use_default` 都缺省时剥掉全部 MCP 工具。`resolve_active_mcp_servers`：`None` 表示隐藏；`[]` 同样隐藏。工具名必须 `{server}_` 前缀才保留。

`ask` / `plan`：`_stamp_turn_conversation_mode`（`processor.py:1479`）丢掉 `mcp_servers` 并把 `skills` 设为 `[]`。`stamp_conversation_mode`（`conversation_mode.py:98`）同时写 `configurable`。Harness `_restrict_ask_plan_config` 再强制一次。

---

## 3. Skills：`SKILL.md` → 过滤 → harness

### 3.1 文件落在哪

| 种类 | 路径 | 谁写 |
| --- | --- | --- |
| Workspace | `skills/<slug>/SKILL.md` | `POST/PUT /api/agents/{id}/skills…`，经 `BackendWorkspace`（`api/routers/skills.py`） |
| Builtin | harness `skill_catalog_roots` 的 builtin 根；Octop 另有 `sync_octop_builtin_skills`（`_post_start_agent`） | 启动同步，不可经 DELETE 删除 |
| Package | `SkillPackageStore.package_skills_dir(package_id)/<slug>/SKILL.md` | `api/routers/skill_packages.py`。挂载条件：backend 是 `local_shell` / `filesystem`，且 `root_dir` 为 `/` 或 agent workspace 根（`manager.py:2058`） |

软删除把 manifest 改成 `removed: true`（`skills.py` 模块说明与 `delete_skill`）。Catalog 看到 `removed` 就跳过（harness `skills/catalog.py` `_collect_skills_from_root`）。

启用的定义：slug **和** frontmatter `name` 都不在 `agent.config.skills_disabled`（harness `is_skill_enabled`）。`skills_disabled_set`（`manager.py:126`）读这个列表。

### 3.2 图编译时交给 harness 的是目录根，不是单份 markdown

`HarnessAgent._init_graph` → `_build_graph` 把

`workspace.skill_paths(extra=config.skills_dir)`

作为 `create_deep_agent(..., skills=...)`（harness `agent.py:1254` 与 `:1721`）。

`skill_paths`（`octop_harness/backends/workspace.py:1180`）包含 builtin 根、workspace `skills/`，以及 `skills_dir` 里的每个包目录。`AgentManager._build_harness_config`（`manager.py:3306`）把 `config["skills"]` 目录加上 `_resolve_skill_package_dirs` 的绝对路径放进 `HarnessAgentConfig.skills_dir`。`skills_disabled` 一并放进 config（`manager.py:3382`），含被关掉的插件 skill 名。

System prompt 里还有一段固定的 slash 说明：`render_slash_skill_prompt`（harness `agent.py:1715`）。它要求模型在用户文本以 `/name` 开头时先读对应 `SKILL.md`。这不是服务端过滤器。

`SkillsMiddleware`（deepagents）负责把这些目录渲染进 prompt，并在 state 里放 `skills_metadata`。`SkillFilterMiddleware`（`octop_harness/middleware/skill_filter.py:151`）在每次 model call：

1. 用 `config.skills_disabled` 与 `skill_identity_keys`（slug + display name）丢掉禁用项。
2. 若 `configurable["skills"]` **存在**（含 `[]`），再按 allow-list 相交。键不存在则保留全部已启用 skill。
3. 禁用 skill 的 `skills/<slug>` / `_builtin_skills/<slug>` 路径会被文件系统工具和 `execute` 拦住。Allow-list 不参与这层拦截，只参与 prompt metadata。

`ChatRequest.to_runnable_config` 仅当 `ChatRequest.skills is not None` 时写入 `configurable["skills"]`。Octop 在 `_build_dashboard_request`（`processor.py:1403`）里：metadata 含 `skills` 键才设置 `request["skills"]`。

`filter_turn_skill_names`（`src/octop/infra/history/trajectory/turn_context.py:21`）只给 trajectory 的 CONTEXT 行，注释写明对齐 `SkillFilterMiddleware`。它不决定模型看到什么。

### 3.3 本回合 `turn.skills` 的服务端路径

`ChatTurnBody.skills`（`api/routers/chat/models.py:46`）：`None` 表示不筛选；`[]` 表示本回合禁用全部 skill。文档字符串与 `validate_chat_skills`（`api/common/validators.py:60`）一致。校验只接受 `list_skill_summaries` 里 `enabled` 的 `name` 或 `slug`。

`prepare_dashboard_turn`（`turn.py:238`）校验后放进 `PreparedDashboardTurn.skills`。`build_dashboard_inbound`（`turn.py:327`）在 `is not None` 时写入 `metadata["skills"]`。

**当前 Dashboard 不走这条路径。** `sendTurnWebSocket`（`dashboard/src/pages/Chat/hooks/chatStore.ts:2564`）写入 `mcp_servers`、`knowledge_base_ids`、model、conversation mode，不写 `skills`。`useChatSend` 把 `parseSkillSlugsInText` 放进 `buildComposerContext`，而 `sendMessage`（`useChat.ts:873`）只把 composer context 挂在本地用户气泡上，不传给 `sendTurn`。所以生产 Dashboard 回合的 metadata 没有 `skills`，harness 使用全部已启用 skill。要做确定性 allow-list，调用方必须自己在 `user_turn` 里带 `skills`。

### 3.4 没有 `/skills/.../reload`

`api/routers/skills.py` 上的路由是 list / get / create / update / delete / enable / disable / import / copy / hub search / hub install / push-to-package。没有 `reload`。

Slash 目录里的 `/skills [list]`（`infra/gateway/slash/catalog.py:246`）是列表命令，不是热重载。

启用 / 禁用：

```
POST /api/agents/{id}/skills/{name}/enable|disable
  → enable_skill / disable_skill（skills.py:1130 / :1146）
  → _skill_disable_keys（slug + frontmatter name，经 harness skill_identity_keys）
  → _persist_disabled
  → AgentManager.persist_skills_disabled（manager.py:1998）
  → persist_harness_config（写入 skills_disabled）
  → sync_skills_disabled（manager.py:2461）
  → HarnessAgent.set_skills_disabled（harness agent.py:334）
```

`set_skills_disabled` 只替换 `self._config.skills_disabled`。不调用 `_init_graph`。`SkillFilterMiddleware` 每次 model call 读的是同一份 config 对象。单测 `test_persist_skills_disabled_does_not_schedule_reload`（`tests/unit/agents/test_agent_manager.py:1881`）断言 `_schedule_reload` 未被调用。

Workspace 新建 / 覆盖 `SKILL.md`（`create_skill`、`update_skill`、hub install 的 `write_files`）不调用 `AgentManager.reload`。若该 slug 已在 `skills_disabled` 里，create / `after_install(enable=True)` 会 `discard` 后 `persist_skills_disabled`。`after_install`（`skills.py:928`）在 `enable` 为假时直接 return，**不会**把 slug 加进 `skills_disabled`。Hub 响应里的 `"enabled": body.enable` 可以是 `false`，而运行中的过滤器仍把该 skill 当作启用。安装路径只 `discard(slug)`，不像 enable 端点那样清掉 display name 键。

### 3.5 `refresh_agents_for_package` 与 `AgentManager.reload` 不是一回事

`refresh_agents_for_package`（`manager.py:2273`）：对 `skill_package_ids` 含该包的未禁用 agent 调用 `sync_skill_package_dirs`。单测断言它不调用 `_schedule_reload`。

`sync_skill_package_dirs`（`manager.py:2145`）：把运行中 agent 的 `config.skills_dir` 换成「配置目录 + 包目录」，然后 `HarnessAgent.reload_subagents()` → `_init_graph()`。这是图重编译，用来让 `skill_paths(extra=skills_dir)` 重新进入 `create_deep_agent`。调用方：包内 skill 的 create / update / delete（`skill_packages.py:504`、`:527`、`:549`）以及 workspace skill push 进包（`skills.py:690`）。

`persist_skill_package_ids`（`manager.py:2117`）同样只 `sync_skill_package_dirs`，不 `update_config_json` 那条会 `_schedule_reload` 的路径。

`AgentManager.reload` / `_reload_agent`（`manager.py:2881`）会 `arebuild_agent`：新 config、新 MCP 占位、gateway 再注入、builtin skill 再同步。进行中的 checkpoint pool 会换掉。技能 enable 不需要、也不应该靠它“生效”。

---

## 4. WebSocket `user_turn` 调用图

```
浏览器 sendTurnWebSocket
  dashboard/src/pages/Chat/hooks/chatStore.ts:2561
  帧 type=user_turn
        │
        ▼
dashboard_chat_ws
  src/octop/api/routers/chat/ws.py:33
  路由 /api/agents/{agent_id}/chat/ws
  UserTurnWsFrame → ChatTurnBody
  turn_has_content 失败 → error + done，不入队
        │
        ▼
prepare_dashboard_turn
  src/octop/api/routers/chat/turn.py:226
  require_agent_row
  validate_chat_mcp_servers
  validate_chat_skills
  mcp_servers 非空 → AgentManager.prepare_chat_mcp
        失败 → OctopError → ws 上 error + done，不入队
  resolve_thread_id
  build_composer_context（历史 chip，不是过滤器）
        │
        ▼
build_dashboard_inbound
  turn.py:306
  InboundMessage
    channel_id = WS_CHANNEL_ID ("octop-dashboard")
    tenant_id = agent_id
    metadata: thread_id, mcp_servers（含 []）, skills（仅当非 None）,
              knowledge_base_ids, model, conversation_mode, …
        │
        ▼
ChannelManager.enqueue(WS_CHANNEL_ID, inbound)
  octop_gateway/manager.py:249
  Gateway.boot 注册 WebSocketChannel(processor=GlobalProcessor)
  src/octop/infra/gateway/gateway.py:248
        │
        ▼
ChannelManager._worker_loop
  gateway manager.py:708
  WebSocketChannel.get_debounce_key 按 thread 加锁
  should_batch_inbound = False（不拼接两条 user_turn）
  handle_inbound
  src/octop/infra/gateway/ws/ws_channel.py:90
  hub.mark_turn_active
        │
        ▼
GlobalProcessor.iter_turn_chunks
  src/octop/infra/gateway/process/processor.py:897
  slash / HITL 短路会自己 yield done 并 return
  否则 _build_dashboard_request（processor.py:1292）
        │
        ├─ build_harness_request
        │    src/octop/infra/gateway/process/harness_request.py:255
        │    messages / thread_id / user / source / model / configurable
        ├─ _resolve_turn_mcp_servers → 可能第二次 prepare_chat_mcp
        ├─ request["mcp_servers"]、request["skills"]
        ├─ _stamp_turn_conversation_mode（ask/plan 清空）
        ▼
AgentManager.stream
  manager.py:1293
  _prepare_stream_request
  harness_manager.stream(agent_id, req)
        │
        ▼
HarnessAgent.stream
  octop_harness/agent.py:475
  ChatRequest.coerce(dict)
  to_runnable_config → configurable.mcp_servers / configurable.skills
  协议 stream
  SkillFilterMiddleware + MCPToolMiddleware 在每次 model call 上过滤
        │
        ▼
iter_turn_chunks 逐 chunk yield
  末尾 yield _done_chunk（processor.py:1226 / :1491）
  type=done，可带 conversation_mode / pending_plan_path
        │
        ▼
WebSocketChannel 对每个 chunk hub.push_to_thread
  推送失败不中断 harness
  finally mark_turn_idle
```

成功回合的 `done` 由 processor 产出、channel 推送。`dashboard_chat_ws` 只在校验失败、空消息、未知帧时自己发 `error` + `done`。断开连接不取消正在跑的回合（`ws.py:184`）。

`prepare_dashboard_turn` 与 `_resolve_turn_mcp_servers` 都会 `prepare_chat_mcp`。第一次在 WebSocket 读循环里，失败则根本不入队。第二次在 worker 里；工具已在 `_mcp_tool_name_set` 时直接返回 `[]`。日志里同一回合出现两条 `prepare_chat_mcp` 是预期，不是双倍加载。第二次应看到 `MCP already ready`。

IM 不走这条 WS 链。`GlobalProcessor.__call__` 用 `project_stream` → `MessageEvent`，`explicit=None`、`apply_defaults=True`，且不设置 `request["skills"]`。

---

## 5. 多 skill + MCP 的确定性诊断

目标：同一条用户文本，固定模型看到的 skill 集合和 MCP 工具集合。

### 5.1 配方

1. **固定 agent 不是 team host。** Team 会丢掉 MCP 与 `skills_dir`。
2. **conversation mode 用 `craft`。** `ask` / `plan` 强制 `skills=[]` 且去掉 `mcp_servers`。Dashboard 在这两种模式下还会把 connectors 发成 `[]`（`useChatSend.ts:127`）。
3. **MCP：在 `user_turn` 里显式带 `mcp_servers`。** 不要依赖“没带键就用默认”。Dashboard 生产客户端总是带数组；脚本客户端若省略该键，会并上 `default_open` 和专家 `mcp_servers`。要关闭，发 `[]`。
4. **名字用运行时的 `mcp_server_name`。** Catalog 是 `{kind}__{instance_id}`。custom-mcp 是用户起的名字（或共享后的 synthetic 名）。`validate_chat_mcp_servers` 用 `list_active_mcp_server_names` 拒绝未知名。
5. **Skills：在帧里显式带 `skills`。** `["slug-a","slug-b"]` 才是 allow-list。`[]` 清空。省略字段等于“全部已启用”。不要用输入框 `/slug` 代替这个字段；那只影响模型是否被 prompt 要求去读文件，不过滤 metadata。
6. **先确认 skill 不在 `skills_disabled`。** Allow-list 与禁用集相交。禁用项不会因为出现在 `turn.skills` 里复活；`validate_chat_skills` 会直接 `NOT_FOUND`（`skill(s) not found or disabled`）。
7. **看两类日志，不要只看 HTTP 200。**
   - `prepare_chat_mcp agent=… requested=… missing=…`，以及 `MCP already ready` / `tools still missing`。
   - harness `MCPToolMiddleware filter: mcp_servers=… active=… mcp=N->M`。`prepare` 成功只说明 `_mcp_tool_name_set` 里有前缀；中间件仍可能因为 server 名不在编译期快照里把工具滤成 0。
8. **Skill 是否进 prompt：看 trajectory CONTEXT 的 `Available skills`，或模型请求前的 `skills_metadata`。** `filter_turn_skill_names` 与中间件同语义，但是旁路记录。Catalog 读失败时 trajectory 会省略该行，不代表 harness 没注入。

### 5.2 陷阱

| 现象 | 原因 |
| --- | --- |
| Dashboard 点了两个 skill，模型仍看到全部 skill | 帧里没有 `skills`。Token 只在本地 composer context |
| 发了 `mcp_servers: []` 仍出现连接器工具 | 多半不是 `default_open` 被服务端加回。查是否另有一条没带该键的调用（IM、Cron 空 picks、自写客户端）。Dashboard 生产路径不会加回 |
| 新会话自动带上 `default_open` 和专家 MCP | 浏览器 `resolveInitialConnectors` 预选后当作显式列表发送。服务端没有第二次合并 |
| custom-mcp 保存后第一回合没有工具 | `PUT /connectors/custom-mcp` 会 `reload_connectors_for_user`（清缓存 + 整实例重建）。重建后的 spec 是 `{}`。工具要等下一回合 `prepare_chat_mcp` 的 `aload`。重建与 in-flight `append_mcp_tools` 会互相覆盖 |
| `prepare_chat_mcp` 返回 `[]`，模型仍然没有该 MCP 工具 | 就绪检查只看工具名前缀。`MCPToolMiddleware.server_names` 是 `_init_graph` 时的快照。名字当时不在 `mcp_server_configs` 会被打成 unknown 并丢掉。另外 `ask`/`plan` 会在进 harness 前删掉 `mcp_servers` |
| 短名字误匹配 | 就绪与过滤都用 `{name}_` 前缀。Server `git` 会撞上 `github_…` |
| Gateway 连接器被误诊断成“需要 reload 才出现” | `mcp_mode=gateway` 走 `inject_missing_gateway_tools`，不走 `reload_connectors`。remote/internal 缺工具才会整实例重建 |
| 启用 skill 后立刻 `AgentManager.reload` | 多余，而且会拆掉已 append 的 custom MCP，直到下一次 `prepare_chat_mcp`。Enable 只更新 `skills_disabled` |
| Hub 安装 `enable: false` 仍出现在 prompt | `after_install` 在 `enable` 为假时什么都不写。默认就是启用 |
| 包里改了 `SKILL.md`，workspace 副本不变 | 包更新走 `refresh_agents_for_package` → 重编译 `skills_dir`。Agent workspace 里若已有同 slug 的 `skills/<slug>/SKILL.md`，`list_skill_summaries` 把 kind 标成 `workspace` 并不再覆盖。运行时目录优先级以 harness `skill_paths` 根顺序为准：后者覆盖前者 |
| 非本地 backend 上看不到包 skill | `sync_skill_package_dirs` 在 backend 不支持 host `skills_dir` 时包目录列表为空 |
| 同一回合两条 `prepare_chat_mcp` | WS 接收循环一次，worker 里 `_resolve_turn_mcp_servers` 一次。第二次应是 already ready |
| `done` 提前出现 | 空消息、校验失败、`prepare_chat_mcp` 在 `prepare_dashboard_turn` 失败，都在入队前由 `ws.py` 直接发 `error`+`done`。入队之后的 `done` 才是 harness 回合结束 |

---

## 6. 相对「enable 然后 reload」的纠正

| 说法 | 代码里的事实 |
| --- | --- |
| 启用 skill 要 `POST /skills/{name}/reload` 或 `AgentManager.reload` | 不存在 reload 路由。`enable_skill` 只 `persist_skills_disabled` → `set_skills_disabled`。单测禁止 `_schedule_reload` |
| `skills_disabled` 要重编译图才生效 | `SkillFilterMiddleware._apply_filter` 每次 model call 读 `self._config.skills_disabled`。`set_skills_disabled` 改的就是这个 frozenset |
| 改包内 `SKILL.md` 也要 `AgentManager.reload` | 要的是 `refresh_agents_for_package` → `reload_subagents` → `_init_graph`，为了把 `skills_dir` 重新放进 `create_deep_agent(skills=...)`。不是 `arebuild_agent` |
| 挂上 skill package 会重启 agent | `persist_skill_package_ids` 只热更新 `skills_dir` 并 `_init_graph` |
| 连接器一保存，custom 工具就留在进程里 | 保存会 `invalidate_mcp_tool_cache` + `reload_connectors`（整实例）。Custom 工具延后到聊天 `prepare_chat_mcp` |
| `default_open` 在 Dashboard 上由服务端强制并集 | 服务端只在 `mcp_servers` 键缺失或 `apply_defaults=True` 时并集。Dashboard 帧带了数组（含空）就原样采用。UI 预选是另一层 |
| 输入 `/pdf` 等于本回合只启用 pdf | 服务端不解析这条 slash 做 allow-list。Prompt 要求模型去读 `SKILL.md`。未禁用的其它 skill 仍在 `skills_metadata` 里 |
| `filter_turn_skill_names` 是注入点 | 它只服务 trajectory。注入点是 `request["skills"]` → `ChatRequest.skills` → `configurable["skills"]` → `SkillFilterMiddleware` |
| Gateway MCP 缺工具时应 `reload_connectors` | `prepare_chat_mcp` 对 gateway 名字调用 `_attach_gateway_tools`，避免拆 checkpoint pool。Builtin remote/internal 才 `reload_connectors` |

---

## 7. 函数索引

| 步骤 | 位置 |
| --- | --- |
| WS 入口 | `dashboard_chat_ws`，`src/octop/api/routers/chat/ws.py:33` |
| 回合准备 | `prepare_dashboard_turn`，`src/octop/api/routers/chat/turn.py:226` |
| MCP 名单校验 | `validate_chat_mcp_servers`，`src/octop/api/common/validators.py:36` |
| Skill 名单校验 | `validate_chat_skills`，`src/octop/api/common/validators.py:60` |
| 入站消息 | `build_dashboard_inbound`，`turn.py:306` |
| 队列 | `ChannelManager.enqueue`，`octop_gateway/manager.py:249`；worker `_worker_loop:708` |
| WS 出站 | `WebSocketChannel.handle_inbound`，`src/octop/infra/gateway/ws/ws_channel.py:90` |
| 回合循环 | `GlobalProcessor.iter_turn_chunks`，`processor.py:897` |
| Dashboard request | `_build_dashboard_request`，`processor.py:1292` |
| Harness dict | `build_harness_request`，`harness_request.py:255` |
| 回合 MCP 合并 | `_resolve_turn_mcp_servers`，`processor.py:1545` |
| 合并规则 | `merge_mcp_servers_with_defaults`，`default_open.py:36`；`ConnectorService.merge_turn_mcp_servers`，`service.py:548` |
| 专家默认 MCP | `AgentManager.default_mcp_servers`，`manager.py:1653` |
| 聊天前加载 MCP | `AgentManager.prepare_chat_mcp`，`manager.py:1669` |
| 连接器整实例刷新 | `reload_connectors` / `reload_connectors_for_user`，`manager.py:1479` / `:1509` |
| 启动 MCP spec | `build_mcp_server_configs_for_user`，`builder.py:505` |
| Gateway 进程内工具 | `inject_missing_gateway_tools`，`builder.py:598` |
| Custom spec | `enabled_harness_configs`，`custom_mcp.py:386` |
| 跳过无 transport | `aload_mcp_tools` / `_connection_spec_loadable`，`octop_harness/mcp.py` |
| 按回合滤 MCP 工具 | `MCPToolMiddleware`，`octop_harness/middleware/mcp_tools.py` |
| Skill 禁用热更新 | `persist_skills_disabled`，`manager.py:1998`；`set_skills_disabled`，harness `agent.py:334` |
| 包热更新 | `refresh_agents_for_package`，`manager.py:2273`；`sync_skill_package_dirs`，`:2145`；`reload_subagents`，harness `agent.py:357` |
| 整实例重建 | `AgentManager.reload` / `_reload_agent`，`manager.py:1376` / `:2881` |
| 按回合滤 skill | `SkillFilterMiddleware._apply_filter`，`octop_harness/middleware/skill_filter.py:256` |
| Catalog 扫 `SKILL.md` | `list_skill_summaries`，`octop_harness/skills/catalog.py:177` |
| 流式入口 | `AgentManager.stream`，`manager.py:1293`；`HarnessAgent.stream`，harness `agent.py:475` |
| 结束帧 | `_done_chunk`，`processor.py:1491`；`iter_turn_chunks` 在 `:1226` yield |
