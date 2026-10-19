# ai-office-deck

单人本地 AI 办公台：把工作资料、会话与已授权日报中的重要行动、风险和建议，整理成有来源、能追溯、人工状态优先的工作清单。MIT。

七个模块：**待办事项、应关注事项、涉诉跟踪、提醒及建议、应付款项、知识库现状、近期工作**。一次显示一个模块；近期工作按北京时间小时合并，每10个日历天一页，更早记录可翻页。支持完成/消除、暂不跟踪、删除、修订历史、保存简报、企业微信账号姓名映射和城市天气。

仓库只含工具、锁定依赖、空配置模板和合成测试，没有作者的数据库、通讯录、工作资料、截图、凭据、定时任务账号或Git历史。第三方原生应用PNG图标不公开分发；包含247个应用名称映射、通用图标回退和本地图标导入方法。

## 安装

已验证主平台：macOS + Node >=22.13 + Python3 + Codex。页面采用 React/Vinext + Cloudflare Worker/D1兼容运行时，Wrangler只监听127.0.0.1。它是个人本地服务，不是多人生产架构。重建和首次采集需本人授权来源。

```sh
python3 bootstrap.py --root "$HOME/.codex/ai-office" --wiki-root /absolute/path/to/WIKI --docs-root /absolute/path/to/documents
cd "$HOME/.codex/ai-office/local-site"
npm ci
python3 setup-selfhost.py --public-url http://127.0.0.1:5199
node scripts/init-local-db.mjs
npm run build
npm run selfhost
```

启动前确认本机5199未被旧实例占用。默认需要所有者登录；私有密码只保存在`.selfhost-owner.json`，不要粘贴到聊天或提交仓库。仅当本人确认回环访问时，才在私有`.dev.vars`设置`LOCAL_NO_PASSWORD="1"`；对公网网址无效。禁止把免密码实例反向代理到公网。

页面：http://127.0.0.1:5199/。首次无数据正常；见 [完整重建教程](docs/REBUILD.md) 设置来源、运行采集和模型整理，最后登记登录自启/半小时采集/每3小时模型任务。无权限的来源显示缺口，不能假称没有工作。

## 代码

- `local-site/app/`：页面及tasks/sync/curate/reminders/resolutions/weather接口。
- `local-site/lib/`：鉴权、证据校验、人工状态保护、小时聚合、分页、天气、姓名显示。
- `local-site/drizzle/`：全部数据库迁移。不要删除已应用迁移或重新建库覆盖旧数据。
- `scripts/`：读取、来源采集、提醒关联、结束确认、检查点和通讯录导入。来源库只读。
- `docs/MODEL_TASK.md`：模型整理规则，按本人路径与授权登记任务。

账号表初始为空。从本人已有WIKI企业微信通讯录导入`userid/name`后重新构建，正文原账号保留；不自动拉取外部通讯录。公开版天气默认北京，可在`lib/weather.ts`及`app/city-weather.tsx`调整显示城市和固定坐标；不获取设备定位。

验证：`npx tsc --noEmit`、`npm run build`；`node --experimental-strip-types tests/history-pages.test.mjs`和`tests/weather.test.mjs`、`tests/wecom-names.test.mjs`；`python3 -m unittest tests/test_sources.py`。接口集成验证使用临时数据库，不用真实业务数据试写。

依赖及应用商标不因本工具MIT许可而变更，见 [第三方说明](THIRD_PARTY_NOTICES.md)。

## 2026-10-19 功能更新

- 待办仅放本人相关或用户明确指定的工作；其他普通工作归关注，司法纠纷归涉诉，付款独立归类。分类、人工结束和删除优先保留，自动整理不能复活。
- 每项可关注/取消，红色重点关注标签独立持久保存；旧优先处理标签不显示。侧栏搜索同时过滤五类事项与数量，无命中显示0，搜索时强调色淡红，清空恢复；付款合计同步显示搜索结果。
- 全模块蓝色顶线；近期工作日期使用YYYY/MM/DD，原始细粒度摘要、北京时间小时归并及每10日翻页保持。
- 知识库现状读取本人WIKI根`质量审计日志.md`，分待用户澄清/WIKI库质量两类；发现先登记，用户明确裁决并实际修正、验证后关闭。`scripts/wiki_quality_audit.py --wiki-root <本人WIKI> list --json`只读；upsert/resolve前核对本人授权。页面数据由`ai_office_wiki_health.py`发布，需已有ops报告与metrics，可在私有config设置wiki_metrics_file。没有数据即说明缺口，不提供作者的问题样本或业务材料。

付款支持手工登记、精确整数分汇总及paid/cancelled排除；企业审批实时采集需本人另接已授权适配器，本仓库不包含任何作者账号或企业应用认证。不能仅因审批通过判定已支付。公开版从空库开始，不恢复作者历史。
