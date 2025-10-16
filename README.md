Volcengine（火山引擎）+ GitHub 运维引导（ops bootstrap）

目的
- 提供一个集中位置，填写资源清单与加密机密，便于我快速落地 CI/CD、GitOps、可观测、安全与备份。

平台入口速查（书签）
- VECR 控制台：`https://console.volcengine.com/cr/`
- VKE 控制台：`https://console.volcengine.com/vke/`
- TOS 控制台：`https://console.volcengine.com/tos/`
- GitHub 组织：`https://github.com/chekdata`
- 飞书开放平台：`https://open.feishu.cn/`

Onboarding 入口
- 新成员创建 Issue：`.github/ISSUE_TEMPLATE/onboarding.md`
- 提交代码走 PR 模板：`.github/PULL_REQUEST_TEMPLATE.md`
- 学习与规范：`ops-bootstrap/研发使用指南.md`
- 模板参考：`ops-bootstrap/templates/`

现在需要你做的（5–10 分钟）
1) 生成 age 密钥（用于 SOPS 加密）
2) 填写 ops-bootstrap/inventory.yaml
3) 在 ops-bootstrap/secrets.enc.yaml 中填入真实机密，并用 SOPS 加密
4) 推送到私有 GitHub 仓库并授予我访问

准备
- macOS: brew install sops age
- Linux: 安装 sops 与 age（按发行版选择包管理器）

步骤 1：创建 age 密钥对（仅一次）
```bash
bash ops-bootstrap/scripts/gen-age-key.sh
```
生成：
- ops-bootstrap/age.pub（可提交到仓库）
- ops-bootstrap/age.key（不要提交；已加入 .gitignore）

步骤 2：替换 .sops.yaml 中的公钥
- 用 `ops-bootstrap/age.pub` 的内容替换占位符 AGE_PUBLIC_KEY_PLACEHOLDER。

步骤 3：填写资源清单
- 编辑 `ops-bootstrap/inventory.yaml`；按字段注释补齐。此文件不放私钥明文，只写你机器上的密钥路径或使用云密钥。

步骤 4：填写并加密机密
```bash
$EDITOR ops-bootstrap/secrets.enc.yaml   # 先明文编辑
sops -e -i ops-bootstrap/secrets.enc.yaml
sops -d ops-bootstrap/secrets.enc.yaml >/dev/null   # 校验可解密
```

如何与我协作
- 建私有 GitHub 仓库并加我为协作者；提交加密后的 secrets 和 `age.pub` 即可（不要提交 `age.key`）。
- 若需要我本地解密并代运维，可通过安全渠道单独提供 `ops-bootstrap/age.key`；否则我将只在需要时提示你本地解密执行。

我会用这些文件完成的事情
- 镜像仓库认证（VECR/Harbor）、GitOps（Argo CD + Rollouts）、可观测（kube-prometheus-stack、Loki/Promtail、Grafana）、备份（Velero→TOS）、策略（OPA Gatekeeper）、可选 Jenkins/GitHub Actions Runner。

发布与回滚（样例）
```bash
# 发布：将 miker-web 构建并推送至 VECR，更新 GitOps apps/miker-web/values.yaml
GITOPS_REPO_DIR=/path/to/infra ./ops-bootstrap/scripts/release.sh miker-web

# 回滚：按镜像标签或 Git 历史修订恢复 apps/miker-web/values.yaml
GITOPS_REPO_DIR=/path/to/infra ./ops-bootstrap/scripts/rollback.sh miker-web <tag-or-revision>
```

注意：release/rollback 依赖以下前置条件
- `ops-bootstrap/inventory.yaml` 已配置 `registry.endpoint` 与 `registry.project`
- `ops-bootstrap/secrets.enc.yaml` 已加密存放 `registry.username/password`
- 本机具备 `docker/git/yq/sops`，并有 GitOps 仓库 push 权限

建议的仓库结构
```text
infra/                 # GitOps 仓库（我会创建或复用你的）
  apps/
  monitoring/
  policies/
  backup/
  argocd/
ops-bootstrap/         # 本文件夹
  inventory.yaml       # 资源清单（不含明文机密）
  secrets.enc.yaml     # SOPS 加密机密
  age.pub              # 公钥（可提交）
  age.key              # 私钥（不要提交）
  scripts/
    gen-age-key.sh
    check-secrets.sh
```

下一步
- 你提交并分享仓库后，把仓库地址发我。我将基于清单与机密执行集群端到端引导。


