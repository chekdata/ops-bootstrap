GitHub 项目分类与管理原则（统一且可执行）

版本：2.0.0｜最后修订：2025-10-25

一、目的与适用范围

- 目的：以 GitHub 为中心，形成“可复用、可审计、可落地”的仓库治理与交付规范。
- 适用：chekdata 组织内所有仓库；与《研发使用指南（统一约定与落地操作）》保持一致，存在冲突时以指南为准并同步修订本文件。

二、层次与分类（从组织到仓库）

- 组织（Organization）：统一成员、权限、计费与策略（飞连 SSO 加入组织）。
- 仓库（Repository）：按“功能域/服务边界”分仓，单一职责；可复用逻辑抽离为独立仓库（SDK/工具/脚手架/CI 模板）。
- 分类建议：
  - 平台与共用：ops-bootstrap（模板与脚本）、infra（GitOps 清单，受保护）、platform-*（共享微服务）。
  - 业务前台：前端仓（如 miker.repo 前端，仅前端）。
  - 业务后端：各服务独立仓，统一模板与门禁。

三、命名与归档

- 命名：语义清晰、可识别，可用前缀表达类别（frontend-、backend-、infra-、common-）。
- 环境/命名空间：<product>-<env>（如 miker-dev/staging/prod）。
- 归档：停用仓库设为 Archive；README 置顶替代仓与迁移说明，不删除历史。

四、分支与环境映射（唯一真源）

- 映射：dev → 开发；staging → 预发；main（打生产标签）→ 生产。
- 保护：main/staging 必须受保护（PR、评审、必需检查、禁止直推、建议线性历史与“对话已解决”）；dev 视团队规模可保护。
- 短生命分支：feature/*、fix/*、hotfix/* 合并即删；标题建议使用 Conventional Commits。

五、质量门禁（Required Checks）

- 必须项（在受保护分支设置为必过）：
  - 规范/类型/单测：lint、typecheck、unit-test
  - 安全：trivy-scan、codeql、gitleaks
- 原则：任一门禁失败即阻断发布；参考附录“必需检查（参考设置）”。

六、制品与镜像（VECR 对齐）

- 构建/推送：统一使用 docker/login-action@v3、docker/setup-buildx-action@v3、docker/build-push-action@v6；凭据来自 REGISTRY_* Secrets。
- 标签：生产 vX.Y.Z（必要时 vX.Y.Z-rc.N）；日常 sha-<short>；记录镜像 digest 便于追溯；严禁 :latest。
- 拉取：集群统一配置 imagePullSecrets: vecr-auth。

七、GitOps 与发布（Argo CD / Rollouts）

- 流程：Push → Actions 构建/扫描/推 VECR → 提 PR 修改 infra 镜像 tag/values → 合并 → Argo CD 同步 → Rollouts 渐进发布/回滚。
- 审批：使用 GitHub Environments 保护生产发布；失败自动通知（飞书），必要时回滚。

八、安全与密钥（最小权限）

- 密钥：仓库/环境 Secrets；优先 SOPS/External Secrets；严禁明文。
- 云访问：优先 IRSA（OIDC 角色）下发最小权限；CI 使用 AK/SK 仅限临时并立即失效。

九、模板与落地（可复制的起步）

- 模板位置：ops-bootstrap/templates/
  - Actions：templates/actions/ci-docker-vecr.yml
  - Docker：templates/docker/Dockerfile.node、.dockerignore
  - Helm：templates/helm/Chart.yaml、values.yaml、templates/{deployment,service}.yaml
  - K8s：templates/k8s/secret-nacos-cred.example.yaml
- 快速开始（示例，将 mysvc 接入 miker-dev）：
```bash
cp -r ops-bootstrap/templates/helm miker.repo/charts/mysvc
cp ops-bootstrap/templates/docker/Dockerfile.node miker.repo/Dockerfile
cp ops-bootstrap/templates/docker/.dockerignore miker.repo/.dockerignore
mkdir -p miker.repo/.github/workflows && \
  cp ops-bootstrap/templates/actions/ci-docker-vecr.yml miker.repo/.github/workflows/ci.yml
# 替换：<product>=miker <service>=mysvc <namespace>=miker-dev <imageRepo>=miker <port>=3000
```

十、通知与审计（飞书）

- 工作流：使用 feishu-notify.yml，由 on: workflow_run 监听 workflows: ["ci"] types: [completed] 触发；可加 workflow_dispatch 手动验证。
- 必需 Secrets：FEISHU_APP_ID/FEISHU_APP_SECRET、FEISHU_CHAT_ID_*（prod/devstg/默认）。
- 报文：使用 msg_type=interactive，content 为“卡片 JSON 字符串”；失败自动降级 text 并重试（指数退避）。

十一、前端项目要点（以 miker.repo 为例）

- 端口与路由：以容器实际监听端口为准（示例 miker-web=3001）；Service 端口名统一 http；Ingress backend 使用 port.name: http。
- 关键变量：USER_API_BASE 必须包含 /api/user（示例：https://benchmark-staging.chekkk.com/api/user）。
- 验证：外部 curl Host 直连 LB；内部 Pod curl 直连应用端口与用户 API。

十二、Nacos / YApi / Ingress（简要对齐）

- Nacos：优先 MSE 托管；namespace=<product>-<env>；以 Secret 下发 address/username/password；配置变更需走 Git→CI→审批→发布。
- YApi：项目 <product>-<env>；只读 Token 用于 CI（Secrets）。
- Ingress：域名 <product>-dev|staging.chekkk.com、<product>.chekkk.com；TLS Secret <product>-tls；与 Rollouts 的双 Service 配合金丝雀。

十三、任务与协作（Projects / Issues）

- Issue：最小工作单元；Labels 标注类型/优先级/模块；Milestones 对齐阶段目标。
- Projects：跨仓看板（Todo → In Progress → In Review → Done）。
- PR 标题规范：推荐 Conventional Commits（feat/fix/chore/docs/refactor...）。

十四、文档与可维护性

- 每仓必备：README（目的/结构/运行/变量）/ CONTRIBUTING（规范/流程）/ CHANGELOG（版本）/ docs（架构与契约）。
- README 结构示例：
```
# 项目简介
- 功能与目标
- 依赖与架构图链接

# 快速开始
- 环境要求（Node/Java/JDK/PNPM…）
- 本地运行命令
- 常用脚本

# 部署
- 环境变量说明
- 构建产物与镜像
- 发布流程（dev → staging → main）

# 贡献指南
- 分支与提交规范
- PR/Issue 模板链接
```

十五、归档与演进

- 归档：设为 Archive，README 顶部写替代仓、迁移日期、兼容窗口与迁移脚本链接。
- 版本演进：打 Tag、维护 CHANGELOG、提供迁移指南，显式标注 Breaking Changes。

十六、统一治理与改进机制

- 周期治理：每季度权限审计、归档清理、依赖升级。
- 模板演进：持续更新前端/后端/库/CI 模板，新仓库一键初始化。
- 契约协作：OpenAPI/GraphQL Schema 版本化；破坏性改动需 RFC/ADR 并附实施与回滚方案。

——

附录 A：必需检查（参考设置）

- 在仓库 Settings → Branches → Branch protection rules 中将以下工作流检查设置为必需：
  - lint、typecheck、unit-test
  - trivy-scan、codeql、gitleaks

附录 B：Feishu 通知工作流触发示例（片段）

```yaml
on:
  workflow_run:
    workflows: ["ci"]
    types: [completed]
  workflow_dispatch:
```

附录 C：CI 构建模板片段（来源：ops-bootstrap/templates/actions/ci-docker-vecr.yml）

```yaml
name: ci-docker-vecr

on:
  workflow_dispatch:
    inputs:
      image:
        description: Image repo path under VECR (e.g. prod/miker-web)
        required: true
        default: prod/miker-web
      tag:
        description: Image tag
        required: true
        default: v0.1.0
  push:
    branches: [ main, dev, staging ]
  pull_request:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - name: Install pnpm
        run: npm i -g pnpm@9
      - name: Install deps
        run: pnpm install --frozen-lockfile
      - name: Lint
        run: pnpm -w lint || true
      - name: Test
        run: pnpm -w test || true
      - name: Preflight DNS
        run: |
          nslookup ${{ secrets.VECR_REGISTRY }} || true
          getent hosts ${{ secrets.VECR_REGISTRY }} || true
      - name: Login VECR
        uses: docker/login-action@v3
        with:
          registry: ${{ secrets.VECR_REGISTRY }}
          username: ${{ secrets.VECR_USER }}
          password: ${{ secrets.VECR_PASS }}
      - name: Build and push
        env:
          REGISTRY: ${{ secrets.VECR_REGISTRY }}
          IMAGE: ${{ github.event.inputs.image || 'devops/example' }}
          TAG: ${{ github.event.inputs.tag || github.sha }}
        run: |
          docker build -t "$REGISTRY/$IMAGE:$TAG" .
          docker push "$REGISTRY/$IMAGE:$TAG"
```


