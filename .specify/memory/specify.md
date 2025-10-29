# 智能流水线规范（Speckit Specify）

版本：1.2.1｜生效：2025-10-12｜最后修订：2025-10-29

## 总体目标

- 以 GitHub 为中心（Actions + Copilot），AI 驱动、可审计、自动化、安全的 CI/CD 流水线。
- 覆盖从代码提交 → 构建 → 测试 → 镜像推送 → K8s 自动发布（VKE） 的全流程。
- Dev/Test/Ops 闭环协作，所有动作可追溯、可分析、可优化；对开发尽可能简单。

## 适用范围

- 平台：GitHub（Actions + Copilot）为主控平台。
- 运行环境：火山引擎（VECR 镜像仓库 + VKE 集群 + TOS 存储）。
- 流程：支持多人协作开发、环境分层（dev / stg / prod）与发布审批。

## 功能诉求

- ✅ 一次提交，自动完成构建、测试与部署。
- ✅ 镜像统一推送到 VECR。
- ✅ 使用 Argo CD / Rollouts 做金丝雀发布与自动回滚。
- ✅ 创建、提交与发布全程通过飞书机器人在群内通知并保留审计痕迹（GitOps）。
- ✅ AI 帮助团队：代码生成、测试建议、日志分析、风险评估（Copilot + 工作流内 AI 步骤）。
- ✅ 自动执行安全扫描（依赖 / 镜像 / secrets）。
- ✅ 团队成员有明确分工与权限边界（环境保护、审批与最小权限）。
- 📘 开发者操作手册：`/Users/jasonhong/Desktop/CICD/ops-bootstrap/研发使用指南.md`（看完即会操作）。
- 📗 当前资源清单：`/Users/jasonhong/Desktop/CICD/ops-bootstrap/资源清单与现状.md`。

## 总体设计

- CI：GitHub Actions（矩阵 + 缓存）承担构建、质量门禁与制品/镜像产出；Copilot 用于 AI 辅助。
- 镜像：使用 `miker.repo/Dockerfile` 构建，推送至 VECR（火山引擎镜像仓库）。
- CD：GitOps（Argo CD + Argo Rollouts）驱动部署与带分析的金丝雀/蓝绿发布，满足自动回滚策略。
- 通知：飞书 Webhook（群机器人）在创建/提交/发布/回滚节点发送消息，保留审计。
- 密钥：仅存于 `/Users/jasonhong/Desktop/CICD/ops-bootstrap/secrets.enc.yaml`（SOPS 加密），通过脚本非交互操作；禁止明文。

## 质量门禁（CI Gates）

按 GitHub Actions 工作流执行：
- 安装依赖：`pnpm install --frozen-lockfile`（启用缓存）。
- 规范与类型：`pnpm lint`、`pnpm tsc --noEmit`。
- 单元测试：`pnpm test`（无测试可暂跳过，建议逐步补齐）。
- 构建产物：`pnpm build`（Next.js standalone）。
- 安全扫描：
  - 依赖扫描：`pnpm audit` 或 `npm audit`（严重级别阻断）。
  - 源码/供应链：GitHub CodeQL（推送与定期扫描）。
  - 镜像扫描：Trivy（构建后对镜像扫描，严重级别阻断）。
  - Secrets 泄露扫描：Gitleaks（PR/推送触发）。

若任何门禁失败则立即终止，不进入发布流程。

## 构建与制品

- 镜像标签策略：`<app>:<git-sha>`，同时生成不可变 `digest` 并记录到构建产物元数据（build metadata）。
- 推送：登录 VECR 后 `docker buildx build --push` 或常规 `docker build && docker push`。
- 所需凭据：`registry.username`、`registry.password`、`vecr.access_key_id`、`vecr.secret_access_key` 等，均来自 `/Users/jasonhong/Desktop/CICD/ops-bootstrap/secrets.enc.yaml`。

## 发布（GitOps）

- 方式：由 GitHub Actions 在“发布阶段”向 GitOps 仓库（`infra/`）提交 PR（或直推受保护分支，经审批后合并），修改镜像标签（或 Helm values），由 Argo CD 同步到 VKE。
- 可观测发布：使用 Argo Rollouts 配置金丝雀策略与 AnalysisTemplate（基于 Prometheus/自定义探针）。
- 审批与环境保护：使用 GitHub Environments（dev/stg/prod）与分支保护规则；`prod` 需指定审批人通过后方可发布。
- 飞书通知：PR 创建、合并、同步、发布完成/回滚均发送到群（含镜像标签与变更摘要）。

## 自动回滚

- 条件触发：
  - 健康检查/探针失败（Readiness/HTTP/GRPC）。
  - 分析阶段 SLO 低于阈值（如成功率 < 99%，P95 延迟 > 规定）。
- 执行方式：Argo Rollouts 自动中止并回滚到上一稳定版本（历史 ReplicaSet）。
- 追溯：记录发布版本、镜像 digest、分析结果、回滚原因到事件系统与日志，并推送飞书通知。

## 手动回滚（一条命令）

- 入口脚本（由运维提供）：`./ops-bootstrap/scripts/rollback.sh <app> <revision-or-image>`。
- 行为：调用 Argo Rollouts/Argo CD 将应用回滚至指定修订或指定镜像标签；输出详细审计日志并发送飞书通知。

## 简单入口（开发者视角）

- 推荐：开发者仅需 `git push` 到受控分支（如 `main`/`production`），GitHub Actions 自动构建/测试/扫描/推送/发版。
- 本地一条命令发布（可选）：`./ops-bootstrap/scripts/release.sh <version|git-sha>`（构建、推送、提交 GitOps 变更、触发同步、等待完成）。

## 可追溯、可分析、可优化

- 追溯项：Git commit、GitHub Actions run id、镜像标签与 digest、Argo 同步版本、Rollouts 历史、分析报告。
- 指标：成功率、错误率、P50/P90/P95/P99 延迟、CPU/内存、重启次数、可用性。
- 产出：
  - 发布报告（包含关键指标与发布耗时）。
  - 回滚报告（包含触发条件与恢复时间）。

## 密钥与凭据

- 统一在 `/Users/jasonhong/Desktop/CICD/ops-bootstrap/secrets.enc.yaml` 管理；通过以下脚本维护：
  - 写入：`./ops-bootstrap/scripts/secret_set.sh <yaml.key.path> <value>`
  - 查看：`./ops-bootstrap/scripts/secret_view.sh`
  - 加密：`./ops-bootstrap/scripts/secret_encrypt.sh`
- GitHub Actions 使用仓库/环境 Secrets 注入运行时；发布脚本在必要时从解密后的环境载入变量（非交互）。

## 最小化工具暴露

- 对开发者：仅需 Git 与 pnpm；发布/回滚通过单入口脚本或 PR 即可完成。
- 对运维：集中维护 GitHub Actions、VECR 凭据与 Argo CD/Rollouts 配置；开发者无需接触底层工具细节。

## 与现有文件对齐

- 构建：复用 `miker.repo/Dockerfile`（Next.js standalone）。
- 运行：本地或容器化使用 `miker.repo/docker-compose.yml` 作为参考示例。
- 密钥：遵循 `.specify/memory/constitution.md` 的加密与治理规范。
- 脚本：可使用 `./ops-bootstrap/scripts/release.sh` 与 `./ops-bootstrap/scripts/rollback.sh` 作为补充入口。

---

## API 文档同步（YApi）

- 分组：公用微服务、SaaS、app、Miker；新建项目默认公开（可读）。
- Token：主分支使用 `YAPI_TOKEN`；dev/staging 可使用 `YAPI_TOKEN_DEV`/`YAPI_TOKEN_STG`。
- 推荐“本地生成”OpenAPI：构建阶段导出 Swagger JSON（路径明确），CI 中调用 `/api/open/import_data` 合并导入。
- 兜底“自动探测”：容器运行后探测常见端口与路径；仅作为临时方案。

## 平台“非生产统一实例”（YApi/Nacos）

- YApi：dev/staging 使用平台统一实例，按项目隔离（`<product>-dev`）。
- Nacos：dev/staging 使用平台统一实例，按命名空间隔离（`<product>-dev`）。
- 好处：无需重复部署，集中治理、统一 SSO、统一权限与审计。

## 单点登录（飞连 SSO）

- OIDC 端点统一：`/api/oidc/*`；回调与信任域按指引配置。
- 用户信息映射：用户名优先 `fullname`/`full_name`/`preferred_username`，邮箱使用 `email`。
- 自动入组：仅对“飞连登录”的用户，自动加入四个分组（公用微服务、SaaS、app、Miker）。

## 证书与网络策略

- 证书：通配 `*.chekkk.com` 仅覆盖单级子域名；多级域名需单独证书。
- LB/安全组：放通 80/443 以及必要 NodePort（如 31409/31833）；集群出网允许 53/80/443。
- DNS 兜底：必要时使用 `hostAliases` 或网关内置解析；长期应以权威 DNS 修复为准。

## 最短路径接入（后端微服务）

1. 在平台 YApi 创建 `<product>-dev` 项目，获取 Token。
2. 在 CI 中生成并导出 OpenAPI JSON；调用可复用工作流推送到 YApi。
3. Nacos 使用 `<product>-dev` 命名空间进行注册与配置；部署时设置必要环境变量（如 `SERVICE_NAME`、`SERVICE_PORT`、`NACOS_NAMESPACE`）。
4. 通过 Ingress 暴露服务并配置 TLS；必要时同步安全组策略。



