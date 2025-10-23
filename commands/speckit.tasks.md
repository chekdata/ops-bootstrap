# Speckit Tasks — miker 生产级 CI/CD 执行清单

版本：1.0.0｜生效：2025-10-12

说明：以下为可执行任务分组清单，支持逐项勾选验收。与《speckit.plan.md》保持一致，覆盖生产 Runner、VECR、GitOps、staging 接入 TOS，以及“多产品共用后端微服务（Mongo+MySQL）”。

## I. miker 生产级 CI/CD（VKE + VECR + ARC）

- [ ] 补齐 `ops-bootstrap/inventory.yaml` 基础信息（`registry.endpoint`、`registry.project`、集群域名）
- [ ] 整理/加密机密：GitHub PAT/Org Secrets、VECR AK/SK 或 OIDC（SOPS 管理）
- [ ] 建立/确认 VECR 项目与命名空间（miker 专用）
- [ ] 准备 GitOps 仓库 `infra/` 并新增 `apps/miker-web`（Helm/Kustomize + Rollouts）
- [ ] 安装 `helm`、`kubectl` 到运维跳板机；校验 `kube.conf`
- [ ] 在 VKE 安装 `cert-manager` CRDs 与 chart
- [ ] 安装 ARC（Actions Runner Controller），创建 `controller-manager` secret（优先 OIDC，其次 PAT）
- [ ] 创建 `RunnerDeployment`（labels: self-hosted, vecr, beijing, miker；requests: cpu:2/mem:4Gi；dind sidecar privileged）
- [ ] 为 ARC/Runner 配置 `imagePullSecrets` 并将 Runner/dind 镜像切换为 VECR 源
- [ ] 校验 Runner 就绪（≥2 副本）、PDB、生效的 `nodeSelector/affinity/tolerations`
- [ ] VPC 出口：为 VKE 子网配置 NAT 网关 + SNAT + EIP（若未配置）
- [ ] 节点 DNS 加固：启用 DoH/DoT（cloudflared 或 systemd-resolved-dot），锁定 `/etc/resolv.conf`
- [ ] 验证 `ghcr.io`/`docker.io`/`actions.githubusercontent.com` DNS 与 HTTPS 通畅
- [ ] 镜像策略：对构建/依赖镜像执行“跨源复制到 VECR”，统一从 VECR 拉取
- [x] 在 miker 仓库添加 CI：pnpm 安装→lint→type-check→test→build→trivy/codeql/gitleaks→构建并推送 VECR（已更新 workflow 并接入 Composite Actions）
- [ ] 发布流程：Actions 修改 GitOps 仓库镜像标签并推送；Argo CD 同步至 VKE；Rollouts 金丝雀 + 自动回滚
- [x] 飞书通知：PR、构建完成、发布开始/完成/回滚 节点消息（已添加 `feishu-notify` 步骤）

## II. staging 环境接入 TOS（上传/下载）

- [ ] 开启 K8s OIDC/IRSA；创建最小权限策略（仅 `<bucket>/miker/staging/*`）
- [ ] `miker-staging` 命名空间创建 `ServiceAccount` 并注解绑定角色
- [ ] 应用 `Deployment` 使用上述 `ServiceAccount`
- [ ] 注入环境：`TOS_ENDPOINT`、`TOS_BUCKET`、`TOS_PREFIX=miker/staging`
- [x] Actions（stg）支持将构建产物同步到 `s3://$TOS_BUCKET/miker/staging/<git-sha>/`（已在 `ci-cd.yml` 增加可选导出步骤）
- [ ] 应用侧采用 S3 兼容 SDK（自定义端点 + path-style）访问 TOS
- [ ] 最小化机密：优先 OIDC/临时凭证；确需 AK/SK 时使用环境层级 Secrets
- [ ] 端到端验证：Pod 获得 STS 并具备 `List/Get/Put`；CI 同步产物可见

## III. 共享后端微服务（Mongo + MySQL）

- [x] 新建 Helm 模块（Deployment/Service/HPA/ServiceAccount/PDB/NetworkPolicy/Secret/ConfigMap）（已生成除 Secret/迁移 Job/备份 CronJob 外的主要模板）
- [ ] 健康探针：`/healthz`、`/readyz`；合理的超时与阈值
- [ ] 资源基线：cpu 200m / mem 512Mi；后续按 P95/吞吐调优
- [ ] 数据库配置：
  - [ ] MySQL：`DATABASE_URL`（优先）或 `MYSQL_*`，连接池参数规范
  - [ ] Mongo：`MONGO_URI`（副本集、`retryWrites=true`、`w=majority`），`readPreference` 可选
- [ ] 机密与轮换：K8s Secret 管理；制定轮换与生效流程
- [ ] 迁移：
  - [ ] MySQL：`flyway/liquibase`（CI 步骤 + K8s Job 双路径）
  - [ ] Mongo：`mongock`/脚本（CI + Job 双路径）
- [ ] 备份：按环境定时备份至 TOS（`s3://<bucket>/shared-svc/<env>/backup/`）与恢复演练
- [ ] 多产品/租户隔离：schema/库/表前缀策略；唯一索引与审计
- [ ] CI/CD：复用 `scan-and-gate.yml`、`build-and-push-vecr.yml`；镜像 `<registry>/<project>/shared-svc:<sha>`
- [ ] GitOps 发布：Rollouts 金丝雀；发布前置 Job 执行迁移；失败自动回滚
- [ ] 可观测：Prometheus/Loki/Tempo 指标与日志；SLO（示例：错误率 <1%，p99 <500ms）与飞书告警

## IV. 组织级可复用工作流与 Composite Actions
（需 org 仓库写权限；当前已在 miker 仓库内提供等效 Composite Actions，org 级暂跳过）

- [ ] 在 `chekdata/.github` 建立复用工作流：
  - [ ] `build-and-push-vecr.yml`
  - [ ] `scan-and-gate.yml`
  - [ ] `gitops-update-and-sync.yml`
  - [ ] `release-with-rollouts.yml`
- [ ] 建立组合动作（Composite Actions）：
  - [ ] `vecr-login`（优先 OIDC 临时凭证，回退 AK/SK）
  - [ ] `feishu-notify`
  - [ ] `setup-node-pnpm`
  - [ ] `export-artifacts-to-tos`
- [ ] 在 miker 与共享微服务仓库通过 `uses:` 方式接入上述工作流/动作

## V. GitHub → 飞书成员同步

- [x] 编写工作流（`schedule` 每日 + `workflow_dispatch` 手动）（已新增 `feishu-sync.yml`）
- [ ] 使用 GitHub GraphQL API 拉取 org/teams 成员；对照映射策略
- [ ] 调用飞书开放平台 API 同步群组/通讯录（增量、幂等）
- [ ] 安全与配额：org-level 环境 Secrets（appId/appSecret/签名密钥）；限流与重试退避
- [ ] 观测：执行日志 + 失败飞书告警

## VI. 验收与回滚

- [ ] 主链路：push→构建/测试/扫描→推 VECR→改 GitOps→Argo 发布（失败自动回滚）
- [ ] 飞书消息：提交、构建完成、发布开始/完成/回滚
- [ ] 回滚：`rollback.sh` 在 1 分钟内恢复
- [ ] staging（含 TOS）：
  - [ ] Pod 通过 IRSA 获取 STS 并访问 `s3://<bucket>/miker/staging/`
  - [ ] Actions 可把构建产物同步到 `<git-sha>/` 前缀
  - [ ] 最小权限策略：无 DeleteObject；跨前缀拒绝
- [ ] 共享微服务：
  - [ ] 迁移 dry-run 与生产前置 Job 成功并可回滚
  - [ ] 稳定连接至 Mongo/MySQL；连接池与重试策略经压测验证
  - [ ] 每日备份可恢复；SLO 满足阈值，异常触发回滚与飞书告警

## VII. 里程碑与排序（建议）

1) 基础设施与 Runner：NAT/SNAT、DNS 加固、ARC + RunnerDeployment、VECR 镜像切换
2) 构建与发布：复用工作流 + miker CI、GitOps + Rollouts、飞书通知
3) staging 与 TOS：IRSA、产物同步、端到端验证
4) 共享微服务：Helm、DB 迁移/备份、SLO 与告警
5) 成员同步：GitHub → 飞书自动化

备注（本轮执行说明）：
- ARC 安装、RunnerDeployment 落地、VECR regcred、NAT/SNAT 与节点 DNS 加固均需集群/云访问权限，当前环境无法直连已跳过；对应脚本与清单已准备（`ops-bootstrap/manifests/*`、`ops-bootstrap/scripts/install_arc.sh`）。
- 共享微服务的 Secret、迁移 Job、备份 CronJob 需结合实际数据库与 TOS 凭证再生成，待接入后补齐。


