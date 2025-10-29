<!--
Sync Impact Report
- Version: template → 1.0.0
- Modified principles: N/A (converted from template to concrete constitution)
- Added sections: 工程原则、安全与密钥、CI/CD 与 GitOps、API 文档与 YApi、身份与访问（飞连 SSO）、配置与服务发现（Nacos）、基础设施与网络、文档与可维护性、变更治理与审批、执行与例外、术语
- Removed sections: 旧的模板执行指南
- Templates requiring updates: 
  ✅ .specify/memory/specify.md（对齐 YApi/Nacos/SSO 与证书/网络策略）
- Deferred TODOs: 无
-->

# 项目宪章（Constitution）

版本：1.0.0｜生效：2025-10-29｜最后修订：2025-10-29

## 宗旨

以 GitHub 为中心（Actions + 可复用工作流），构建安全、可审计、易扩展、AI 赋能的工程与发布体系；
坚持最短路径、少即是多，以高质量可测试 MVP 持续迭代，服务于稳定交付与业务快速试错。

## 工程原则

- 代码风格与质量
  - 必须遵循 Google 代码规范；后端代码需有必要的说明性注释，确保可读可维护。
  - 模块解耦，按微服务边界设计，接口清晰，便于在其他项目中复用与同步。
  - 倡导高内聚、低耦合，函数/变量命名语义明确，拒绝过度设计。
- 交付策略
  - 以可测试的 MVP 为先，逐步增强；每次改动可回滚、可追溯。
  - 默认通过 CI 自动执行构建、测试、扫描、发布；失败即止。

## 安全与密钥

- 密钥管理
  - 禁止将明文凭据提交仓库；统一存放于加密文件（SOPS）或 GitHub Secrets。
  - 默认最小权限原则；对需要网络访问的命令明确申请权限并记录。
- 安全基线
  - 开启依赖/镜像/Secrets 泄露扫描（CodeQL/Trivy/Gitleaks 等）。
  - 生产环境受保护分支与审批门禁，操作全量审计留痕。

## CI/CD 与 GitOps

- 平台与流水线
  - 以 GitHub Actions 为唯一构建与发布入口，优先复用组织级工作流（`chekdata/.github`）。
  - 工作流触发：push/PR/schedule/手动；支持矩阵与缓存，加速构建。
- 交付落地
  - 镜像统一推送 VECR；部署由 Argo CD 驱动，并可选 Rollouts 金丝雀/蓝绿与自动回滚。
  - 通过 GitOps 对环境变更进行版本化管理与审批。

## API 文档与 YApi

- 项目与分组
  - 按业务分组：公用微服务、SaaS、app、Miker；默认项目公开（可读）。
  - 使用项目 Token 进行文档导入，主分支默认生效；dev/staging 可配独立 Token。
- 文档同步
  - 推荐“本地生成”OpenAPI（构建阶段导出明确路径），然后调用 YApi `/api/open/import_data` 合并导入。
  - 提供“自动探测”兜底方案，但以可重复、可控的本地生成为准。

## 身份与访问（飞连 SSO）

- OIDC 接入
  - 统一使用 `/api/oidc/*` 端点；回调与信任域按指引配置。
  - 用户属性映射：用户名优先 `fullname`/`full_name`/`preferred_username`，邮箱使用 `email`；
    邮箱前缀作为用户 ID 以兼容 YApi 插件行为。
- 组自动加入
  - 仅对“通过飞连登录”的用户，自动加入四个分组（公用微服务、SaaS、app、Miker）。

## 配置与服务发现（Nacos）

- 平台“非生产统一实例”
  - dev/staging 共享平台实例，按命名空间隔离（如 `<product>-dev`）。
  - 服务注册需集成 Nacos 客户端或轻量注册器（sidecar/SDK），包含心跳与健康检查。

## 基础设施与网络

- 证书与域名
  - 通配证书 `*.chekkk.com` 仅覆盖单级子域名；多级域名需专门证书。
  - 生产域名优先使用受信 CA（如 Let’s Encrypt + cert-manager）。
- 负载均衡与安全组
  - 放通 80/443 与必要 NodePort（如 31409/31833）；集群出网允许 53/80/443。
  - 对 DNS 异常场景可使用 `hostAliases` 或网关内置解析兜底（临时措施）。

## 文档与可维护性

- 统一文档
  - 开发者指南：`ops-bootstrap/研发使用指南.md` 为单一真相源。
  - README 需列出目录结构、可重用脚本与“不应提交”的清单与检查项。
- 可追溯性
  - 每次构建/发布需产出可追溯元数据（commit、run id、镜像 digest、发布记录）。

## 变更治理与审批

- 环境保护
  - `prod` 必须走 PR 与审批；`dev/stg` 可根据策略自动化发布但保留审计。
- 版本与发布
  - 语义化版本；发布说明包含变更摘要、影响面与回滚指引。

## 执行与例外

- 默认强约束，例外需：
  - 记录业务场景与风险评估；
  - 获得对应负责人批准；
  - 在下一版本评审中复盘并决定是否固化为规则。

## 宪章治理

- 版本策略（SemVer）
  - MAJOR：删除/重定义原则或不兼容治理变更。
  - MINOR：新增原则或显著扩展指导。
  - PATCH：表述澄清、无语义变更。
- 修订流程
  - 由平台负责人提出修订 PR，团队评审通过后合并；
  - 修订须同步检查相关模板与指南文件并对齐。
- 审查节奏
  - 每月例行检查一次；重大事故或变更后即刻复盘并必要时修订。

## 术语

- YApi：接口文档平台，支持 OpenAPI 合并导入。
- Nacos：服务发现与配置中心，支持命名空间隔离。
- GitOps：以 Git 为声明源的持续交付模式，由 Argo CD 同步。
- Rollouts：Argo 金丝雀/蓝绿与分析回滚组件。
