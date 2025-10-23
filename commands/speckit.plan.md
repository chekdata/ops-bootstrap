# 项目整理与 miker 生产级 CI/CD 规划（Speckit Plan）

版本：1.2.0｜生效：2025-10-12｜最后修订：2025-10-12

## 一、项目文件夹整理（MVP）

目标：保持仓库干净、可执行、可维护；临时文件集中、可清理；脚本与清单可复用。

1) 目录归类
- `ops-bootstrap/`：运维引导、密钥、脚本、清单与清理脚本。
- `commands/`：团队规范与流水线规范（已含 constitution/specify/plan）。
- `miker.repo/`：应用源码（Next.js）。
- `tmp/`：临时与二进制，仅本地使用；定期清理，不提交。

2) 临时与二进制清理（保持在 tmp/）
- 保留：`tmp/` 下各类 runner/helm 压缩包、工具二进制、临时配置。
- 迁移：若有散落的临时脚本/产物，统一移入 `tmp/` 或 `ops-bootstrap/scripts/` 并注释用途。

3) 需要保留的脚本（运维/CI 相关）
- `ops-bootstrap/scripts/secret_*`：机密管理（SOPS）。
- `ops-bootstrap/scripts/release.sh`、`rollback.sh`：GitOps 发布/回滚。
- `ops-bootstrap/scripts/gen-age-key.sh`：加密密钥生成。
- 其他与 ARC/Runner/Feishu 同步相关脚本保留（统一在该目录）。

4) 后续清理策略
- 新增 `ops-bootstrap/scripts/cleanup_tmp.sh`：按文件模式清理 `tmp/`，保留最近 N 天必要文件。
- 新增 `.gitignore`（如需）避免临时文件提交。

## 二、为 miker 仓库搭建生产级 CI/CD（VKE）

目标：以 GitHub Actions + GitOps（Argo CD/Rollouts）为中心，构建→测试→扫描→镜像→发布→自动回滚。

适用仓库：`https://github.com/chekdata/miker`

环境矩阵（与发布策略）：
- dev：开发自测；自动构建 + 可选自动发布。
- stg（staging）：联调与预发布；与 TOS 集成（对象存储上传/下载）。
- prod：生产；强门禁（评审 + 扫描 + 审批），金丝雀发布，失败自动回滚。

阶段 A：准备
- 补齐 `ops-bootstrap/inventory.yaml`：`registry.endpoint`、`registry.project`、集群域名等。
- 用 `secret_set.sh` 写入并加密仓库/VECR 等机密。
- 准备 GitOps 仓库 `infra/`，新增 `apps/miker-web`（Helm/Kustomize + Rollouts）。

阶段 B：构建与镜像
- 在 miker 仓库添加 GitHub Actions 工作流：安装 pnpm→lint→type-check→test→build→trivy/codeql/gitleaks→构建并推送 VECR。
- 镜像命名：`<registry>/<project>/miker-web:<git-sha>`。

阶段 C：发布与回滚
- Actions 在发布阶段修改 GitOps 仓库镜像标签并推送；Argo CD 同步到 VKE。
- Rollouts 配置金丝雀策略 + AnalysisTemplate（Prometheus/SLO），失败自动回滚。
- 保留飞书通知：PR/发布/回滚节点推送。

阶段 D：网络与 DNS 加固（生产必要）
- VPC 出口：确保 VKE 节点子网已绑定 NAT 网关与 SNAT 规则；EIP 正常。
- DNS：节点级启用 DoH/DoT（cloudflared 或 systemd-resolved-dot）；加固 `/etc/resolv.conf` 只读；为 `ghcr.io`、`docker.io`、`actions.githubusercontent.com` 等关键域名设置校验与可观测。
- 镜像策略：优先“跨源复制到 VECR”（避免公网拉取失败），工作负载统一从 VECR 拉取；必要时配置 `imagePullSecrets` 与 registry mirrors。

阶段 D：文档与权限
- 完成 `ops-bootstrap/研发使用指南.md` 中“从 push 到上线”的章节与权限分工（dev/stg/prod 保护规则）。
- 最小权限：仓库/环境 secrets、VECR 凭据与只读 Token 的限制。

阶段 E：staging 环境 TOS 集成（上传/下载）
- 目标：`miker` 在 `stg` 环境具备将资产/中间产物上传至 TOS、应用读取/写入的能力；不下发长期明文 AK/SK。
- 集成要点：
  - K8s 侧启用 OIDC/IRSA，创建授信角色与最小权限策略（仅 `<bucket>/miker/staging/*`）。
  - 在 `miker-staging` 命名空间建立 `ServiceAccount` 并绑定角色（注解方式）。
  - 应用 `Deployment` 引用该 `ServiceAccount`；通过环境变量注入：`TOS_ENDPOINT`、`TOS_BUCKET`、`TOS_PREFIX=miker/staging`。
  - CI（Actions）如需直传构件到 TOS，使用仓库/环境 Secrets 注入端点/桶（优先使用 OIDC / 临时凭证）。
- 端点规范：`https://tos-<region>.volces.com`（如：`https://tos-cn-beijing.volces.com`）。
- 参考实现：见 `ops-bootstrap/研发使用指南.md` 的“（新增）TOS 访问指南（应用/微服务/CI）”。

环境 Secrets（最少集）：
- 通用：`REGISTRY_ENDPOINT`、`REGISTRY_USERNAME`、`REGISTRY_PASSWORD`、`REGISTRY_PROJECT`、`GITOPS_REPO_CLONE_URL`、`GITOPS_REPO_TOKEN`。
- staging 专用：
  - `TOS_ENDPOINT`（例：`https://tos-cn-beijing.volces.com`）
  - `TOS_BUCKET`（例：`chek-backup`）
  - 可选：`TOS_AK`、`TOS_SK`（临时凭证；若已用 IRSA 可不设）

工作流差异（stg）：
- 在 `stg` 流水线“发布后步骤”中，增加可选步骤：将构建产物（如前端静态资源包、Sourcemap 或导出文件）同步至 `s3://$TOS_BUCKET/miker/staging/<git-sha>/`。
- 应用侧使用 S3 兼容 SDK（自定义端点 + path-style）访问 TOS。

阶段 F：自托管 Runner（VKE + ARC + VECR）
- 方案：在 VKE 内安装 ARC（Actions Runner Controller）与 RunnerScaleSet，Runner 镜像与 dind 镜像全部托管在 VECR；使用 `imagePullSecrets`。
- 依赖：安装 cert-manager CRDs 与 chart；创建 `controller-manager`（GitHub PAT 或更优 OIDC App）secret；Runner 使用专用 `ServiceAccount` 与 `PodSecurityContext`。
- RunnerDeployment 规范：labels `self-hosted, vecr, beijing, miker`；Requests：`cpu:2/mem:4Gi` 起步；挂载 emptyDir 给 dind；启用 `--privileged` 给 dind sidecar。
- 可靠性：副本≥2；`PodDisruptionBudget`；`nodeSelector`/`affinity` 绑定稳定节点；`tolerations` 允许调度到专用池。

阶段 G：组织级可复用工作流与 Composite Actions
- 在 `chekdata/.github` 建立：
  - 可复用工作流：`build-and-push-vecr.yml`、`scan-and-gate.yml`、`gitops-update-and-sync.yml`、`release-with-rollouts.yml`。
  - 组合动作（Composite Actions）：`vecr-login`（动态登录，优先 OIDC 获取临时凭证，回退 AK/SK）、`feishu-notify`、`setup-node-pnpm`、`export-artifacts-to-tos`。
- miker 仓库中仅 `uses:` 调用上述工作流/动作，参数化镜像名、命名空间、环境与门禁阈值，降低维护成本。

阶段 H：GitHub → 飞书成员同步（自动化）
- 触发：`schedule` 每日与手动 `workflow_dispatch`。
- 流程：GitHub GraphQL 拉取 org/teams 成员 → 对照映射配置 → 调用飞书开放平台 API 同步到指定群组/通讯录；仅增量变更。
- 安全：飞书 appId/appSecret、签名密钥保存在 org-level 环境 Secrets；最小权限；请求限流与重试退避。

## 三、后端微服务（跨产品共用｜Mongo + MySQL）

目标：为一个被多个产品共用的后端接口服务提供统一的 CI/CD 与运行基线，安全接入 Mongo 与 MySQL，具备迁移、备份与可观测。

运行约束：
- 不直接下发长期明文数据库凭据；优先使用 K8s Secret + 定期轮换，或通过 OIDC/动态凭证代理。
- 最小权限：应用用户仅具备必要 schema 的 CRUD 与迁移权限。

部署形态（Helm 模块）：
- 组件：`Deployment`、`Service`、`HPA`、`ServiceAccount`、`PodDisruptionBudget`、`NetworkPolicy`、`Secret`（DB、TLS）、`ConfigMap`（只放非机密配置）。
- 就绪/存活探针：`/healthz`、`/readyz`；优先 HTTP 探针，超时与阈值根据冷启动调优。
- 资源：起步 `cpu: 200m/ mem: 512Mi`，按 P95 延时与吞吐调参。

配置与 Secrets：
- MySQL：`MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_DB`、`MYSQL_USER`、`MYSQL_PASSWORD` 或 `DATABASE_URL`（优先）；连接池（最小 1、最大按副本*并发测算）。
- Mongo：`MONGO_URI`（含副本集、`retryWrites=true`、`w=majority`）；读写分离按需配置 `readPreference`。
- 备份：按环境将热备与全量备份推送至 TOS（前缀：`s3://<bucket>/shared-svc/<env>/backup/`）。

迁移与数据管理：
- MySQL：`flyway`/`liquibase` 作为 CI 步骤与 Job（K8s）双路径执行；生产只读门禁→审批→执行。
- Mongo：`mongock` 或自研迁移脚本；同样以 CI + K8s Job 双路径执行。
- 租户/多产品隔离：库/表前缀或 schema 隔离；严格唯一索引与审计日志。

CI/CD 衔接：
- Reusable workflow `scan-and-gate.yml` 报警即止；`build-and-push-vecr.yml` 产出镜像 `<registry>/<project>/shared-svc:<sha>`。
- 部署使用 GitOps（Argo Rollouts 金丝雀 + 自动回滚）；发布前置 Job 运行迁移；失败自动回滚并告警。

可观测与 SLO：
- 指标：p50/p90/p99 延时、错误率、数据库连接耗尽、慢查询；采集至 Prometheus + Loki + Tempo。
- SLO：错误率 < 1%，p99 < 500ms（示例）；违反触发回滚与通知（飞书）。

## 三、一条命令式操作（示例）

发布：
```bash
GITOPS_REPO_DIR=/path/to/infra ./ops-bootstrap/scripts/release.sh miker-web
```

回滚：
```bash
GITOPS_REPO_DIR=/path/to/infra ./ops-bootstrap/scripts/rollback.sh miker-web <tag-or-revision>
```

## 四、验收标准（MVP）

- 开发者 push 到 main → 自动构建/测试/扫描 → 推送镜像 → 提交 GitOps → Argo 发布完成（或自动回滚）。
- 飞书消息记录完整链路：提交、构建完成、发布开始/完成/回滚。
- 任一门禁失败自动停止并可追溯；回滚操作可在 1 分钟内完成。

staging（含 TOS）专项验收：
- `miker-staging` 命名空间内 Pod 可通过 IRSA 获取 STS 并对 `s3://<bucket>/miker/staging/` 进行 `List/Get/Put`。
- GitHub Actions 可将构建产物同步到上述前缀（保留 `<git-sha>/` 层级）。
- 最小权限策略生效：无 DeleteObject 权限；跨前缀访问被拒绝。

后端微服务专项验收：
- CI 对 MySQL/Mongo 运行迁移 dry-run 通过；生产发布前置迁移 Job 成功并可回滚。
- 服务在 VKE 内可稳定连接至 Mongo 与 MySQL，连接池与重试策略符合压测阈值。
- 每日备份产物在 TOS 可验证恢复；Metrics 满足 SLO，异常触发 Rollouts 回滚与飞书告警。


