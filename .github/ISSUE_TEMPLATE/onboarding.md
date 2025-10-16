---
name: 团队成员 Onboarding（运维仓库）
about: 为新成员开通账号与落地环境的 checklist（ops）
title: "[Onboarding] {姓名}/{邮箱}"
labels: onboarding, ops
assignees: ''
---

## 基本信息
- **姓名**：
- **企业邮箱**：
- **GitHub 用户名**：
- **入组日期**：
- **部门/角色**：

## 账号开通
- [ ] GitHub org 及 team 权限（dev/ops）
- [ ] VECR 项目读/写（`devops`/`miker`）
- [ ] VKE 访问（dev/stg/prod，最小权限）
- [ ] 飞书群与通讯录
- [ ] Nacos / YApi / Ingress-NGINX（按需）

## 本地环境
- [ ] 安装 `kubectl`/`helm`/`age`/`sops`/`yq`
- [ ] 克隆 ops 仓库与 `infra` 仓库
- [ ] 配置 `.sops.yaml` 与 `ops-bootstrap/age.pub`

## CI/CD 与发布
- [ ] 了解 GitOps（Argo CD/Rollouts）
- [ ] 学会使用 `release.sh` / `rollback.sh`

## 资料速查
- [ ] `ops-bootstrap/研发使用指南.md`
- [ ] `commands/speckit.plan.md` / `commands/speckit.tasks.md`
- [ ] `ops-bootstrap/templates/`

## 备注
- 首次发布建议双人确认与回滚演练。


