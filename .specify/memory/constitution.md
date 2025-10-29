<!--
Sync Impact Report
- Version: 1.2.0 → 1.2.1
- Modified principles: 九、身份与密钥记录与加密规范（路径与脚本示例修正）
- Added sections: 无
- Removed sections: 跟踪项中的 TODO(COMMANDS_DIR)、TODO(SECRET_FILE_PATH)
- Templates requiring updates:
  ✅ README.md（SpecKit commands 说明已调整为“业务仓自行软链/引入”）
  ✅ .specify/memory/specify.md（secrets 路径对齐）
- Deferred TODOs: 无
-->

# 团队宪章（Speckit Constitution）

版本：1.2.1｜生效：2025-10-12｜最后修订：2025-10-29

## 一、宗旨与适用范围

- 本宪章适用于本仓库及后续所有项目与子仓库，优先级高于历史习惯。
- 目标：以高质量、可测试、最小可行产品（MVP）为导向，减少冗余与过度设计，统一语言为简体中文。

## 二、代码风格与静态检查（谷歌代码规范）

- 统一遵循谷歌代码规范（按语言对应的 Google Style Guide）。若与现有 Lint/格式化工具冲突，以团队配置为准并尽快对齐。
- 机械化检查为准绳：Lint/格式化/类型检查必须通过后方可合并。

### 2.1 TypeScript/JavaScript
- 遵循 Google JavaScript/TypeScript 风格；使用 `eslint` 与项目内规则执行静态检查。
- 类型优先：`pnpm type-check` 必须通过；禁止 `any` 滥用（仅限必要边界处）。
- 导出/公共 API 明确类型；避免不必要的 `try/catch`；用早退代替深层嵌套。

### 2.2 Shell
- 遵循 Google Shell 风格：脚本需具备可读性与可维护性。
- 头部统一：`#!/usr/bin/env bash`、`set -euo pipefail`、`IFS=$'\n\t'`、`LANG=C`。
- 不使用交互式输入；脚本必须支持非交互参数，且具备幂等性。

### 2.3 Python（若使用）
- 遵循 Google Python 风格；推荐 `ruff`/`flake8` 检查，`pytest` 测试。
- 严禁随意全局可变状态；模块职责单一。

### 2.4 文档与 Markdown
- 面向执行的文档为先：提供可复制的一步一条命令；不出现 `dquote>` 或省略号 `...`。
- 文档中的长命令统一以“脚本文件”的方式提供。

## 三、火山引擎（Volcengine）使用原则

- 唯一权威：一切使用方法以火山引擎“官方文档”为唯一来源，并在 PR 描述中附上对应官方文档链接与版本/日期。
- 身份与密钥：密钥、令牌等敏感信息采用安全存储与最小权限原则；严禁写入仓库明文。
- IaC/自动化优先：可用时优先使用基础设施即代码或官方 CLI/SDK；禁止手工配置无法复现的步骤。
- 非交互执行：所有 CLI/SDK 调用必须可非交互运行（传入 `--yes`、`--assume-yes`、`--non-interactive` 等）。

## 四、命令与自动化规范

- 一步一条命令：文档与脚本中的每一步为一条可独立复制执行的命令，禁止省略任何关键信息。
- 自动衔接：脚本需通过退出码与必要的输出解析自动衔接到下一步；失败时立即停止并打印可定位日志。
- 长指令落地为脚本：当命令过长或包含多参数/多行内容时，直接新建本地脚本文件，编辑好后再执行；禁止靠终端粘贴长文本入参。
- 状态记录：需要跨步骤传递上下文时，使用显式的状态文件（如 `.state/` 目录）或参数，不依赖隐式 shell 历史。

示例（质量门禁一键执行，非交互且可串行自动化）：

```bash
pnpm install --frozen-lockfile && pnpm lint && pnpm type-check && pnpm build
```

当步骤繁琐时，使用脚本文件：

```bash
cat > scripts/ci.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'
LANG=C

pnpm install --frozen-lockfile
pnpm lint
pnpm type-check
pnpm build
EOF
chmod +x scripts/ci.sh

./scripts/ci.sh
```

## 五、项目整洁与文件治理

- 仓库保持干净：删除无必要文档与过期脚本；临时资料统一放入 `tmp/` 或对应模块的 `docs/tmp/` 并定期清理。
- 不使用占位符与临时方案：任何 TODO/样例/占位必须在合并前转为可执行与可测试的最小实现，或明确移除。
- 目录命名与现有规范一致：组件用 PascalCase，工具函数用 kebab-case；跨项目保持一致性。

## 六、测试与 MVP 原则

- MVP 先行：每次改动以最小可行为准，避免过度设计；先跑通核心路径，再扩展。
- 可测试性：至少具备类型检查门禁；新增关键逻辑应附单元测试或可验证脚本；接口需有可复现的调用示例。
- 回归保障：修复缺陷需附带最小复现测试或可执行复现步骤。

## 七、质量门禁与提交规范

- 合并前必须通过：
  - 代码规范与格式（Lint/格式化）
  - 类型检查（TypeScript `pnpm type-check`）
  - 构建（`pnpm build` 或对应产物构建）
- 提交信息（Commit/PR）：
  - 以中文简明描述“做了什么 + 为什么”；引用需求/工单编号（若有）。
  - 变更若涉及火山引擎，附官方文档链接与变更风险评估。

## 八、治理与修订

- 本宪章高于一切口头习惯；任何例外必须在 PR 中书面说明，并在合并前获批。
- 修订流程：提交 PR → 说明背景/变更点/迁移方案 → 评审通过后生效，更新本文件的版本与日期。
- 新项目与子仓库必须在初始化时纳入本宪章；差异需显式说明。

- 版本策略（SemVer）：
  - MAJOR：破坏性治理调整（删除/重定义原则或与现有流程不兼容）。
  - MINOR：新增原则或对现有原则进行实质性扩展。
  - PATCH：表述澄清、错别字修正、无语义性微调（本次属此类）。

- 合规复审：
  - 每次 PR 审核须核对是否符合本宪章中“质量门禁/安全/发布流程”等硬性要求；
  - 每月进行一次例行自检，记录偏差并在当月内以 PR 修复或豁免说明。

---

附：在 `miker.repo/` 中的推荐本地质量门禁命令（可直接复制执行）：

```bash
cd miker.repo && pnpm install --frozen-lockfile && pnpm lint && pnpm type-check && pnpm build
```

## 九、身份与密钥记录与加密规范（secrets.enc.yaml）

- 记录位置（唯一）：仓库根目录 `secrets.enc.yaml`（repo‑relative）。
- 加密要求：只提交 SOPS 加密后的文件，禁止在仓库中存放任何明文机密。
- 结构要求：以分组键存放（如 `github.token`、`volcengine.access_key_id`、`registry.username` 等），保持 YAML 合法且可被工具解析。
- 来源要求：凡新发给或过程产生的身份与密钥，须“当次即刻”写入上述文件并提交（不允许暂存于临时/个人本机笔记）。
- 非交互与可复现：使用提供的脚本非交互写入，具备幂等与原子性写入保障。

一条命令（脚本）写入示例：

```bash
./scripts/secret_set.sh volcengine.access_key_id "<VALUE>"
```

脚本行为：
- 自动解密到临时文件 → 使用 `yq` 设置目标键值 → 使用 `sops` 重新加密并覆盖原文件 → 清理临时文件；失败即停并返回非零码。
- 依赖：`sops`、`yq` 已安装并可用；SOPS 的密钥来源由本地环境或仓库配置决定。

## 十、ops-bootstrap（运维启动仓库）更新原则

- 定位与边界
  - `ops-bootstrap` 是团队 DevOps 基线与模板的“单一真源”，用于存放模板、规范与可复用脚本；不承载业务代码。
  - 仓库默认私有；仅按需授予最小权限的读写；对外项目以“复制模板 + 本地化改造”的方式复用。

- 变更流程（强制）
  - 只能通过 PR 合并到 `main`；禁止直接 push。
  - 合并前必须通过质量门禁（Lint/类型/构建/必要安全扫描）。
  - 涉及模板的 PR 必须在 `templates/README.md` 更新“Verified <YYYY-MM-DD>（<环境/项目>）”标记，并给出最小验证步骤与结果。
  - 涉及云平台能力（VE、MSE、VECR 等）的 PR，描述中附官方文档链接与版本日期。

- 目录与禁区
  - `_local/**`、`tmp/**` 永久忽略；禁止提交 kubeconfig、私钥、明文机密、生产真实数据。
  - 不在本仓库提交 `miker.repo` 等业务仓库代码；仅保留模板与说明。
  - 镜像与脚本应与 `研发使用指南.md` 的规范一致，命名与占位符保持统一（`<product>/<service>/<namespace>/<port>`）。

- 模板管理（templates/）
  - Actions：
    - `actions/ci-docker-vecr.yml` 用于构建并推送到 VECR；统一使用 Secrets：`REGISTRY_ENDPOINT/REGISTRY_USERNAME/REGISTRY_PASSWORD`。
    - `actions/vecr-mirror.yml` 用于将公共镜像（Docker Hub/GHCR）镜像到 VECR；可选使用 `DOCKERHUB_USERNAME/DOCKERHUB_TOKEN`、`GHCR_USER/GHCR_TOKEN`。
    - 飞书通知 Composite Action `actions/feishu-notify/`，工作流内 `uses: ./templates/actions/feishu-notify` 并传入 `FEISHU_WEBHOOK`。
  - Helm：`helm/` 提供 Deployment/Service/values 骨架；全部镜像引用遵循 VECR 命名：`chek-images-cn-beijing.cr.volces.com/<project>/<image>`；标签固定版本（禁止 `:latest`）。
  - K8s：
    - `k8s/arc-runnerdeployment.yaml`：使用 `summerwind/actions-runner`（带 ARC wrapper）并已验证；如需 Docker 构建，开启 `dockerdWithinRunnerContainer`。
    - `k8s/coredns-vecr.yaml`：统一 CoreDNS 配置（上游 1.1.1.1/8.8.8.8/114.114.114.114），镜像来源 VECR。
    - `k8s/secret-nacos-cred.example.yaml`：示例 Secret；生产建议改用 External Secrets。

- Nacos 使用原则（MSE 托管优先）
  - 生产/预发布/开发优先使用火山引擎 MSE Nacos；以 Namespace `\<product>-\<env>` 做环境隔离，以 Group 做业务隔离。
  - 配置变更走“代码 → CI 校验 → 审批 → 自动发布到 MSE”，禁止控制台直改；敏感项走 Secrets/External Secrets。
  - 监控告警接入飞书；重大变更前需有备份/快照；如自建仅作兜底（3 节点 + 外部 RDS）。

- 安全与机密
  - Secrets 统一走仓库 Secrets 或 SOPS/External Secrets；PAT/Token 需最小权限并开启组织 SSO 授权。
  - 严禁在仓库中提交任何明文机密；示例中以占位符与说明替代。

- 回滚与兼容
  - 模板变更须注明是否破坏性；提供迁移指南或兼容层（如保留旧输入参数一段过渡期）。
  - 遇到回滚：首选 Git Revert；必要时发布兼容修复版本，并在 `README.md` 与 `研发使用指南.md` 标注。

- 记录与同步
  - 重要变更需在 `README.md` 或模板 `README` 追加“变更记录/验证记录”。
  - 与业务仓库的同步采取“复制更新 + PR”方式；不得引入子模块造成耦合。

