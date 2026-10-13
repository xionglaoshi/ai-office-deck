# 完整重建与运行说明

本文件与仓库源码用于功能重建。它不会复原未备份的私人历史、提醒服务账号、系统许可或外部资料库。私人恢复包如存在，先校验其清单；不得把它提交本公开仓库。源码以本仓库锁定版本为准，不能以标题相同的旧教程覆盖当前实现。

## 目的与信息范围

办公台用于让本人辨认当前行动、督办依赖、工作异常/风险和可参考建议，有摘要也有原始日期/证据。日报中的所有员工TODO不能变成本人的任务；计划与来源自述完成须显式区分；没有期限/新完成证据不能推断逾期。建议不能伪装已经部署。所有AI工作仅涉及已授权的本地输入，不自动外发、改源文件、改权限、执行业务操作。

读取链：已授权来源→半小时只读采集→候选与sourceCatalog保存→每3小时模型读正文、人工状态和结束保护→curate保存稳定实体/修订/简报→合适tracking项同步macOS提醒→真实GET读回→完整成功才推进检查点。网页刷新只读取，不等于采集或模型任务执行。

来源实现位于`scripts/ai_office_sync.py`和`ai_office_sources.py`：Codex近14天非归档主会话；WIKI项目/公司/决定/会议未勾选线索；企业微信近21天日报全部分片、正文、评论；近90天会议与关注正文；近30天研究/行业、本地邮件页；问题/重点涉诉风险按风险读取器；WPS近14天文件元数据；Computer History近30天真实10分钟摘要。图片/附件数量显示未读，采集不默默OCR。日报读取以原report_time为日期，journal_uuid去重，长来源分块不丢失；文件mtime不证明业务状态。实时企业微信/邮箱/WPS云端正文不在此代码中凭空出现，需要本人另行已授权的来源工具先同步本地。

## 结构及状态契约

- 页面三类`tracking/risk/advice`及历史模块。旧task/attention/decision通过迁移兼容；不得换ID重建旧状态。
- `tasks`保存人工字段、done(0开放/1已处理/2不用管)、deleted、manual_override和updated；`sync_state`保存latest、curated、source:/source-version:、detail:、revision:、brief:、resolution:/subject:及reminders；另有迁移日志。完整备份要保留整个D1状态及其元数据，不能只导出开放清单。
- `sourceId`沿采集记录稳定，sourceVersion保留原证据版本。新具体事项使用subjectKey生成UUIDv5，namespace为d10f6e54-7d95-48c0-bc50-8520b870689e；key包含对象/项目/具体问题，不能只用标题、分类或时间。跨日报同一具体事项合并证据，标题相似不是合并依据。
- `/api/sync` POST只更新候选及来源，失败源保留旧有效内容；`/api/curate` POST校验snapshotAt、expectedItems、证据sourceId和版本、稳定身份与结束保护。人工编辑/完成/删除/不用管优先，自动整理不能改名绕过墓碑或复活。输入成功返回及GET读回均确认才算保存。
- `evidence`至少含sourceId/date/reporter/location/excerpt/type(reported/document/verified/suggestion)，必要时version。详情正文不截成短卡片；摘要、最新进展、责任及待确认、下一步、缺口分别显示。`brief:`内容幂等保存，修订历史及旧证据不由latest覆盖。
- `/api/tasks` GET供网页读全量事项、历史/来源正文；POST人工新增/编辑/状态/软删除，origin与所有者鉴权，并发expectedUpdated；`/api/reminders`和`/api/resolutions`沿ID与关联处理，不以同名推断同一提醒/同一业务。

完整schema和校验规则以`drizzle/`、`lib/office-data.ts`、`lib/task-policy.ts`与对应route.ts为准，保留全部迁移。不要自行加请求时CREATE TABLE、篡改迁移日志或清空已存在数据库。

## 从零安装

1. 取得仓库或教程内已校验源码。Node最低22.13（当前验收Node实际版本记录随发行），Python3，macOS提醒还需CLT Swift、osascript与已授权访问。先检查已安装路径；不要升级全机环境。使用package-lock固定版本，不混用pnpm锁。
2. `python3 bootstrap.py --root "$HOME/.codex/ai-office" --wiki-root /本人/WIKI --docs-root /本人/文档库 --history-root /本人/电脑历史摘要`。目标存在则停止，核对原数据后选择新目录。首次无源则空输入目录明确显示缺口。配置只归自己，勿照抄作者账号。
3. 进入local-site执行`npm ci`（可用的本人代理显式设置，不改系统网络），`python3 setup-selfhost.py --public-url http://127.0.0.1:5199`。程序生成600权限`.dev.vars`和`.selfhost-owner.json`，不打印秘密。已有配置不要覆盖。浏览器密码由本人查看私有交接文件，登录正常需要它；接口用serviceToken，cookie不是服务令牌。
4. `node scripts/init-local-db.mjs`应用全部迁移；`npx tsc --noEmit --incremental false`和`npm run build`；`npm run selfhost`。只绑定回环，不绑定0.0.0.0，不自动公开网页；5199端口有旧实例先核对不能同时启动。
5. 验证未授权的service接口返回401，所有者网页可读写，不能打印Authorization/私有正文到外站。真实业务不使用测试数据试写。合成测试在隔离新库验证人工优先、墓碑、并发、长正文、完整源/失败源回退、重复简报、分页和姓名边界。
6. 配置自己的codex_root/codex_db/wiki_root/wps_root/history_root/local_service_file/exclude_thread/proxy。关注正文默认WIKI内meetings/assistant-notes，可用config的focus_folders指定本人真实目录。来源根要由本人确认，存在的陌生目录不能擅自替换。排除办公台整理会话和Automation，以免自己产生循环任务。
7. 先用`ai_office_sync.py --dry-run`核对来源（它会只读来源，不上传）；无权限则解决本人许可并标缺口。首次正式采集由用户恢复授权后运行。`ai_office_access.py read`会输出私人工作材料，仅留本人本地。按MODEL_TASK.md逐项整理，写本地work JSON，`curate --file`保存和读回。409时重读重判断，不盲目重放。
8. 提醒可选。必须先由本人选定原生清单，把准确list ID写config，不新增猜测清单。Python读取配置允许清单，JXA只能处理该清单。检查已有授权；没有权限让本人系统授权，不自动改变系统许可。`ai_office_reminders.py --dry-run`只读规划，不创建/修改/推进关联账本。tracking明确需要提醒才remind=true；risk/advice=false。实际同步沿已核ID创建/同步完成，不跨端删除，不恢复人工删除，不覆盖既有原生提醒标题和精确时间。
9. 最后登记任务，再进行一次真实读回。成功标准不是退出码0，而是来源覆盖、模型保存、提醒核对及readbackVerified。部分成功不得推进model-review-checkpoint.json；重启不能把人工状态归零。

## 页面与辅助功能

白底中文、北京时间，左侧固定四项菜单，宽屏右侧仅所选模块，窄屏菜单在内容顶部。各模块有开放/完成或消除/暂不跟踪，计数取真实全量，不限制前N条。主卡短摘要、进展、责任、下一步，证据/完整原稿/修订可展开；原始日期与期限分开。底部折叠同步覆盖/模型整理/提醒状态，缺口不能被成功0掩盖。

近期工作从原10分钟摘要及会话材料变化按小时归并，原始摘要/时间不改；跨整点段归相关小时、末整点不造多余桶、跨日北京时间边界、迟到记录进原小时、稳定ID去重。第一页今天及前9日，后续每10日一页，底部上一页/下一页/页码及范围；无记录日期仍按日历，不改成10条或10个有数据日。

`lib/wecom-users.json`仅userid→name及快照来源元数据。`scripts/ai_office_contacts.py`从本人WIKI通讯录导入，不联网，不导入电话、邮箱、部门等其他字段；同账号冲突、空/数量不完整则保持旧表。重新构建后当前和未来卡片自动转换，区分大小写和完整token，不替换路径/链接/邮件/源ID。保留原账号及原文，未知不猜填，不据通讯录快照推断在职。

图标名表247种应用，macOS信息MobileSMS等常见系统/办公/浏览器/开发工具都能显示名称。默认通用AppWindow，不把bundle ID作为大块文本。未来未知应用同样通用回退，图片加载失败回退。私有恢复包保留本机原生PNG；公开仓库仅名称表与通用图标，不把第三方商标许可声明为MIT。要增加本地图标：从本人已安装App的Info.plist确认CFBundleIdentifier/名称，再用NSWorkspace的icon(forFile:)或对应icon文件与sips生成26~64pxPNG，在`public/app-icons/manifest.json`填本地`/app-icons/<bundleID>.png`路径，保留原名称，构建验收后仅留本机。

天气Open-Meteo固定城市坐标、当天current和daily，页面当天状况/当前气温/最低最高/时间/来源；15分钟缓存，10秒请求限时，缺失/跨日/过旧(3小时)不伪造晴天或0度。公开默认北京；私人版可设本人授权城市。无需定位/第三方密钥，不传姓名或工作资料到天气服务。

## 定时任务

bootstrap生成两个未登记LaunchAgent：网页登录自启KeepAlive与半小时采集StartInterval=1800，实际ProgramArguments用当前Node/Python绝对路径。`~/Library/LaunchAgents`只登记指向项目launchd内的软链接，勿覆盖已有其他任务。模型整理由Codex既有本地任务每3小时执行，完整提示在MODEL_TASK.md：北京时间00/03/06/09/12/15/18/21。用当前应用支持的automation工具/界面登记，先查已有任务，原id有效则更新；原thread已不存在先建立本人新整理任务，再关联，禁止照搬其他人的target_thread_id。复制toml不代表App已登记，任务配置不代表已实际执行；需要核对下一触发时间和实际日志/读回。模型服务登录、订阅及额度不是zip可恢复的授权。

登记方法示例（恢复属于用户授权，若只阅读教程不要执行）：

```sh
mkdir -p "$HOME/Library/LaunchAgents"
ln -s "$HOME/.codex/ai-office/launchd/com.ai-office.local.plist" "$HOME/Library/LaunchAgents/com.ai-office.local.plist"
ln -s "$HOME/.codex/ai-office/launchd/com.ai-office.sync.plist" "$HOME/Library/LaunchAgents/com.ai-office.sync.plist"
launchctl load "$HOME/.codex/ai-office/launchd/com.ai-office.local.plist"
launchctl load "$HOME/.codex/ai-office/launchd/com.ai-office.sync.plist"
```

存在同标签/旧路径先核对，不重复启动。日志可限量保留，work仅本轮整理JSON和当前服务日志；旧包/构建测试副本不是运行资产。node_modules可使用runtime依赖最小集；未来构建前npm ci恢复完整锁定依赖，源码和数据库永远不能当缓存删除。运行进程依赖不能在未验证替代前剪掉。

## 已知故障与处置

| 现象 | 原因/处理 |
|---|---|
| 页面只有候选、没有完整简报 | collect不等于curate；不能限制只原候选ID/本人待办前N条。读所有相关正文，拆稳定subjectKey，多证据入库，保留brief:/detail:/revision: |
| WIKI/WPS PermissionError而终端可读 | macOS TCC责任进程不同。先核对背景Python实际路径/责任身份与文件提供商许可；不要换目录或运行主体绕过拒绝。让本人按最窄有效范围授权，完整磁盘是更宽的候选，需本人决定 |
| 0条但源目录失效 | 缺失/空/遍历异常必须error与coverageGap，保留旧有效候选/事项；目录存在不证明已读取 |
| WIKI AssertionError / Codex OperationalError | 路径迁移、缺目录、数据库版本/rollout模式变更。核对已授权正本路径、现时schema及JSONL字段，保留旧成功位置；不猜替代路径 |
| 来源显示账号、未知app一大串ID | 导入已核通讯录；图标manifest和fallback覆盖MobileSMS/未知项，不猜姓名或丢原账号 |
| 完成/不用管又出现 | 不能换ID/subjectKey、按原标题重建、用自动值覆盖manual_override；读墓碑及并发更新时间，沿原身份 |
| 长正文/日报漏项 | 全部分片/正文/评论、分块catalog及source-version，识别excerptOnly/未OCR；不能只抓标题或截前N |
| build报seatbelt/workerd权限、localhost阻断 | 构建/本机连接需要当前工具环境审批。先核实锁定版本，使用受允许环境；不得关闭安全沙盒或改系统网络 |
| SQLite在线backup无法打开文件 | 不试写真实库。短停所有写入者做冷复制，复制主库/元数据及必要WAL，finally恢复服务；校验复制库与表行数/键摘要 |
| localhost浏览器混用云端 | 必须在资料所在用户Mac浏览器验证该Mac的127.0.0.1，不用父云localhost |
| launchctl bootstrap失败 | 当前系统可用load/unload登记；检查plist和实际标签状态，不能把退出码当网页成功 |
| 直接wrangler启动未加载SELF_HOSTED | 必须使用run-selfhost.mjs启动，它会准备dist/server/.dev.vars；不能漏配置而进入Sites鉴权分支 |
| 固定示例selfhost-db逻辑ID | 是本地逻辑绑定，不是真人云数据库。迁移只针对自己的持久目录，不能重新生成绑定映射导致旧库消失 |
| Sites访问403 | 已知有实际个案；本机模式不依赖Sites。不要不断换公开范围/token试绕过，不能宣称Sites永久不可用 |
| 天气过期/失败 | 当天和3小时有效性检查，标暂未更新，保留来源；不制造温度或拉取位置 |
| 还原后提醒ID找不到 | iCloud原提醒需同账号恢复；保留账本先核对，别按同名自动配对或重建原删除提醒 |

## 备份与验证清单

完整私人恢复包应包含：源码/锁/全部迁移/图标/姓名表、当前D1整个目录的冷快照、config及owner私有配置、提醒关联账本、模型检查点、真实当前模型任务导出/提示词、两个LaunchAgent/外部兼容软链接说明、运行说明、重建脚本、文件SHA256与权限清单；离线依赖包标架构和Node版本。不要包含旧源码副本、测试数据库、日志大集合、外发包和原Git历史。备份存本人私有地点，600文件权限；凭据缺失可新生成本地服务凭据，但不等于恢复外部账号权限。

验证CRC/每文件SHA256、SQLite integrity_check、全部表行数及稳定ID/人工状态/墓碑/来源/简报保留；在新临时空库完成构建、登录、未授权401与合成用例，真实数据库只能只读核对。重启后实际网页GET、两个launchd状态、模型任务登记和下一触发时间均确认。源码相同不代表数据相同，自动任务存在不代表来源可读或模型已完成。
