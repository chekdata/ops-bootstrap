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
- CI/CD：在应用仓库接入 `templates/actions/ci-docker-vecr.yml`，统一构建→扫描→推送 VECR。
- 镜像与部署：Helm 模板见 `templates/helm/`；K8s 示例见 `templates/k8s/`。
- 文档与规范：统一在本仓库维护，应用仓库只引用与落地。

### 不要提交什么
- `_local/**`、`tmp/*`、私钥（如 `age.key`）、明文机密、个人 kubeconfig。
- 如果需要保存敏感信息，请存放于 `_local/` 并确保 `.gitignore` 正确忽略。

### 团队约定（摘）
- 分支保护：`main` 需 PR + CI 通过；禁止直接 push。
- 安全：Secrets 通过 SOPS/环境注入；最小权限；定期轮换。
- 发布与回滚：采用 GitOps（Argo CD/Rollouts），PR 合并后自动发布，失败自动回滚。

### 遇到问题
- Onboarding 或权限问题：新建 Onboarding Issue。
- CI/CD 或模板问题：提 PR 并附上自检清单（见 PR 模板）。
