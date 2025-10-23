## ops-bootstrap（运维启动仓库）

### 这个仓库做什么
- 为团队提供一套统一、可复用的 DevOps 基线：CI/CD、GitOps、镜像规范、环境与账号规范、操作指引。
- 面向多产品/多环境（dev/stg/prod），强调最小权限与可审计。

### 仓库结构
```text
ops-bootstrap/
  .github/               # PR/Issue 模板（onboarding、变更自检）
  templates/             # 可复用模板（Actions/Helm/Docker/K8s）
  研发使用指南.md         # 面向团队的完整操作与约束（四段式）
  README.md              # 本文档（目的、用法、目录）
```

### 快速开始（团队）
1) 阅读 `研发使用指南.md`（四段式：基本原则 → 环境装配 → 团队流程 → QA）
2) 新成员创建 Issue：`.github/ISSUE_TEMPLATE/onboarding.md`
3) 新特性按 PR 模板提交：`.github/PULL_REQUEST_TEMPLATE.md`
4) 复制 `templates/` 中需要的模板到你的项目并按需修改

### 使用方式（建议流程）
- CI/CD（GitHub）：
  - 构建与镜像：`templates/actions/ci-docker-vecr.yml`（VECR）或 `templates/actions/ci-docker-ssh-deploy.yml`（任意 Registry + SSH 部署）
  - 集群部署（推荐）：`templates/actions/ci-helm-deploy.yml`（Helm 到 prod 集群）
- 镜像与部署：Helm 模板见 `templates/helm/`；K8s 示例见 `templates/k8s/`。
- 服务治理：注册 Nacos、接口管理入驻 YApi，遵循服务命名、环境命名与网关规范。
- 文档与规范：统一在本仓库维护，应用仓库只引用与落地。

### 不要提交什么
- `_local/**`、`tmp/*`、私钥（如 `age.key`）、明文机密、个人 kubeconfig。
- 如果需要保存敏感信息，请存放于 `_local/` 并确保 `.gitignore` 正确忽略。

### 团队约定（摘）
- 分支保护：`main` 需 PR + CI 通过；禁止直接 push。
- 安全：Secrets 通过 SOPS/环境注入；最小权限；定期轮换。
- 发布与回滚：采用 GitOps（Argo CD/Rollouts），PR 合并后自动发布，失败自动回滚。

### 多微服务“快速纳管”到 prod 集群（对齐 Nacos + YApi）
1) 制品统一：每个服务的 Docker 镜像命名遵循 `<registry>/<imageRepo>/<service>:sha-<short>`，应用仓库复用 `ci-docker-vecr.yml` 或 `ci-docker-ssh-deploy.yml` 完成构建与推送。
2) 集群发布：使用 `ci-helm-deploy.yml` 调用 Helm Chart（`templates/helm`），按服务名、命名空间、端口覆盖 `values`；首次会自动创建命名空间。
3) 服务发现（Nacos）：
   - 应用容器内注入 `NACOS_SERVER_ADDR`、`NACOS_NAMESPACE`、`NACOS_USERNAME`、`NACOS_PASSWORD` 等环境变量（通过 `values.yaml` 的 `env`/`envFromSecret`）。
   - 应用在启动时向 Nacos 注册并保持心跳（语言 SDK 自行选择）。
4) 接口管理（YApi）：
   - 统一在 YApi 建项目与环境，CI 里在构建后执行 `yapi-cli`/OpenAPI 同步（可在各应用仓库添加一个 `sync-yapi` job）。
5) 网关与域名：
   - 通过 Helm 的 `ingress.yaml` 模板落域名与证书；遵循 `svc.prod.example.com` 命名；证书由平台统一下发到集群 Secret。
6) 回滚与多版本：
   - 镜像回滚：重跑 workflow 指定旧 `image_tag`。
   - 发布策略：建议接入 Argo Rollouts（蓝绿/金丝雀），与 Actions 解耦。

### 最小改造“从单机容器迁移入集群”的步骤（每个服务）
1) 补齐 Dockerfile 健康检查与配置注入（环境变量/Secrets）。
2) 在服务仓库新增 `.github/workflows`：
   - 构建推送：引用 `ci-docker-vecr.yml` 或 `ci-docker-ssh-deploy.yml`（如使用非 VECR）。
   - 集群部署：新增 workflow 调用 `ci-helm-deploy.yml`，传入 `service`、`namespace=prod`、端口与镜像信息。
3) 平台侧准备：
   - 集群 GitHub Runner（参考 `templates/k8s/arc-runnerdeployment.yaml`）
   - Secrets：`KUBECONFIG_B64`、`IMAGE_REGISTRY`、镜像拉取 Secret `vecr-auth`。
4) 数据持久化（避免重下数据/OSM）：
   - 在 `values.yaml` 开启 `persistence.enabled: true`。
   - 若已有数据盘或 NFS：设置 `existingClaim`；否则指定 `storageClass` 与 `size` 自动创建 PVC。
   - `mounts` 定义挂载点（例如 OSM 数据目录），容器内路径与本地一致即可无痛迁移。
5) Nacos & YApi：
   - 创建 `Secret` 保存 Nacos 凭据，在 `values.yaml` 使用 `envFromSecret` 注入。
   - 在 Actions pipeline 末尾增加接口同步步骤（可选）。
6) 触发 main 发布，完成纳管。

### 遇到问题
- Onboarding 或权限问题：新建 Onboarding Issue。
- CI/CD 或模板问题：提 PR 并附上自检清单（见 PR 模板）。
