## ops-bootstrap（运维启动仓库）

### 这个仓库做什么
- 为团队提供一套统一、可复用的 DevOps 基线：CI/CD、GitOps、镜像规范、环境与账号规范、操作指引。
- 面向多产品/多环境（dev/stg/prod），强调最小权限与可审计。

### 仓库结构
```text
ops-bootstrap/
  .github/               # PR/Issue 模板（onboarding、变更自检）
  templates/             # 可复用模板（Actions/Helm/Docker/K8s）
  scripts/               # 工具脚本（无密钥；用于镜像、清单、列表等）
  tools/                 # 通用工具（Kaniko Dockerfile 等，无集群机密）
  apps/argocd/           # 示例清单（建议视作 examples，而非生产真源）
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

### 使用 SpecKit — SDD（与 GitHub SpecKit 对齐）
- 项目：参考 GitHub SpecKit 的 README 以了解完整工作流与目录结构（memory/scripts/templates）
  - 链接：github/spec-kit（见 README）
  - 地址：`https://github.com/github/spec-kit`
- 本仓已预置与 SpecKit 兼容的目录与脚本（无需二次搭建）：
  - `.specify/commands/`：
    - `speckit.constitution.md`、`speckit.specify.md`、`speckit.plan.md`、`speckit.tasks.md`
  - `.specify/`（软链 → `ops-bootstrap/.specify/`）：
    - `memory/constitution.md`
    - `templates/{plan-template.md,spec-template.md,tasks-template.md,agent-file-template.md,checklist-template.md}`
    - `scripts/bash/{create-new-feature.sh,setup-plan.sh,update-agent-context.sh,check-prerequisites.sh,common.sh}`
- 在 Cursor/SpecKit 中直接使用（示例）：
  - `/speckit.constitution  .specify/commands/speckit.constitution.md`
  - `/speckit.specify  .specify/commands/speckit.specify.md  "<你的功能描述>"`
  - `/speckit.plan  .specify/commands/speckit.plan.md`
  - `/speckit.tasks  .specify/commands/speckit.tasks.md`
- 重要说明：以上命令依赖 `.specify/` 的模板与脚本；本仓已将 `.specify/` 目录内置到 `ops-bootstrap/` 下统一维护，路径对 Cursor/SpecKit 恒定可用。

#### 将本仓的 SpecKit 能力下发到业务仓（推荐：子模块 + 软链）
```bash
# 在业务仓根目录执行：
git submodule add -b main <your-git-url>/ops-bootstrap ops-bootstrap
git submodule update --init --recursive

# 建立软链，保证 SpecKit 固定查找路径
ln -s ops-bootstrap/commands commands
ln -s ops-bootstrap/.specify .specify
git add .gitmodules ops-bootstrap commands .specify
git commit -m "chore(spec-kit): add ops-bootstrap submodule and SpecKit symlinks"
```

- 升级：在业务仓执行 `git submodule update --remote ops-bootstrap` 获取平台最新模板/脚本。
- 验证：在业务仓打开 Cursor，运行 `/speckit.specify .specify/commands/speckit.specify.md "<功能描述>"`，应在 `specs/` 下生成新的规范目录。

### Spec‑Driven Development（SpecKit）
- 工具：使用开源 `github/spec-kit` 实现 Spec‑Driven Development（SDD）。参考项目主页与 README 了解命令与流程：[github/spec-kit](https://github.com/github/spec-kit)
- 本仓输出目录（供 SpecKit 直接使用）：
  - `.specify/commands/`：Speckit 命令定义与说明
  - `.specify/`（软链，实际位于 `ops-bootstrap/.specify/`）：模板、脚本与内存（constitution）
- 在 Cursor/SpecKit 中直接触发命令示例：
  - `/speckit.constitution  .specify/commands/speckit.constitution.md`
  - `/speckit.specify  .specify/commands/speckit.specify.md`
- 引入到业务仓库（推荐子模块 + 软链）：
  ```bash
  git submodule add -b main <your-git-url>/ops-bootstrap ops-bootstrap
  ln -s ops-bootstrap/commands commands
  ln -s ops-bootstrap/.specify .specify
  git add .gitmodules ops-bootstrap commands .specify
  git commit -m "chore: add ops-bootstrap submodule with SpecKit links"
  ```
- 注意：SpecKit 默认在仓库根查找 `.specify/commands` 与 `.specify/`，本仓已内置对应目录结构。

### 不要提交什么
- `_local/**`（任何本地密钥/令牌/个人配置）
- `tmp/**`（一次性/环境特定脚本与中间产物、kubeconfig、证书等）
- 任何 kubeconfig/凭据/证书/私钥（例如：`**/*kubeconfig*.{conf,yaml}`、`**/*-tls.*`、`**/*.pem`、`**/*.json` 中包含 Token）
- 账户/令牌类文件（例如：`vecr_login.env`、`yapi_tokens.json`、`yapi_bmo_token.json` 等）
- 个人或组织通讯录映射等敏感数据（例如：`mappings/feishu_userid_to_enterprise_email.yaml`）

> 如需保留环境落地脚本，请将通用化内容迁移到 `templates/` 或 `scripts/`，并剔除所有密钥/域名/IP/账号等敏感信息。

### 建议共享（团队复用）
- `templates/**`
  - Actions：`ci-docker-vecr.yml`、`ci-helm-deploy.yml`、`feishu-notify`、`k8s-secret-check`、GitLab 兼容模板
  - Helm：`Chart.yaml`、`templates/`、`values.yaml`、`examples/`
  - Docker：`docker/Dockerfile.node`
  - K8s：常用组件与操作示例（不含 kubeconfig/证书）
- `scripts/**`
  - `vecr_*` 镜像/仓库脚本、`probe_vecr_manifest.py`
  - `gen_feishu_mapping_from_xlsx.py`（如含个人数据，仅限私有仓库使用）
- `tools/**`
  - `kaniko/Dockerfile` 等通用工具
  - 排除任何携带集群凭据的 `.conf/.yaml`（如存在，勿提交）
- `apps/argocd/**`
  - 作为示例展示（建议迁入 `templates/helm/examples/`），生产真源应在专门的 `infra` 仓库由 GitOps 管理
- 文档：`研发使用指南.md`、`GitHub 项目分类与管理原则.md`

### 上传到 chekdata/ops-bootstrap 之前的检查清单
1) `git grep -nE "(password|secret|token|Authorization|AKIA|AKLT|-----BEGIN)"` 不应有命中
2) 目录仅包含上文“建议共享”的内容；`_local/` 与 `tmp/` 已从提交中排除
3) 模板中引用的复用工作流路径正确：
   - `uses: chekdata/.github/.github/workflows/yapi-sync-reusable.yml@main`
   - `uses: chekdata/.github/.github/workflows/yapi-sync-autodetect.yml@main`
4) 文档中的域名、分组、命名空间等已对齐最新规范（四分组；平台非生产统一实例）