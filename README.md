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
  secrets.enc.yaml       # SOPS 加密的机密文件（仓库根目录，建议）
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
- 常用脚本：`templates/scripts/create-namespace.sh`（一键创建命名空间并下发基础配额/策略）

  使用示例：
  ```bash
  # 本地 kubeconfig + 完整命名空间
  ./templates/scripts/create-namespace.sh \
    --kubeconfig /path/to/kubeconfig \
    --namespace miker-prod

  # 本地 kubeconfig + 组合命名
  ./templates/scripts/create-namespace.sh \
    --kubeconfig /path/to/kubeconfig \
    --product miker --env prod

  # 远程快速执行（需按需替换仓库 RAW URL 和 kubeconfig 路径）
  curl -fsSL "<YOUR_RAW_URL>/ops-bootstrap/templates/scripts/create-namespace.sh" | \
    bash -s -- --kubeconfig /path/to/kubeconfig --product miker --env prod
  ```
- 服务治理：注册 Nacos、接口管理入驻 YApi，遵循服务命名、环境命名与网关规范。
- 文档与规范：统一在本仓库维护，应用仓库只引用与落地。

### 使用 SpecKit — SDD（与 GitHub SpecKit 对齐）
- 本仓不内置 `.specify/commands/` 命令文件；如需在业务仓使用 SpecKit 命令，请按以下方式引入：
  - 方案 A（推荐）：直接从开源仓库 `github/spec-kit` 引入命令模版。
  - 方案 B：将 `ops-bootstrap` 作为子模块引入后，在业务仓自行创建 `.specify/commands/` 并维护命令文件。
- 在业务仓引入 `ops-bootstrap` 的示例：
```bash
# 在业务仓根目录执行：
git submodule add -b main <your-git-url>/ops-bootstrap ops-bootstrap
git submodule update --init --recursive

# 可选：建立软链，保证 SpecKit 固定查找路径
ln -s ops-bootstrap/.specify .specify
# 如需命令目录，请在业务仓创建并维护：
mkdir -p .specify/commands
# 将需要的 speckit.*.md 命令文件放入该目录

git add .gitmodules ops-bootstrap .specify
git commit -m "chore(spec-kit): add ops-bootstrap submodule and SpecKit links"
```

### Spec‑Driven Development（SpecKit）
- 工具：使用开源 `github/spec-kit` 实现 Spec‑Driven Development（SDD）。参考项目主页与 README 了解命令与流程：[github/spec-kit](https://github.com/github/spec-kit)
- 本仓输出目录（供 SpecKit 模板/内存直接使用）：
  - `.specify/`：模板与内存（constitution/specify），可被业务仓软链复用

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