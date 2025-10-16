# 模板使用说明（复制→替换占位符→提交）

目录结构：

- actions/ci-docker-vecr.yml：通用 GitHub Actions，构建并推镜像到 VECR，再触发 GitOps（可选）。
- helm/：通用 Helm Chart（Deployment/Service/values）。
- docker/Dockerfile.node：Node.js/Next.js 生产镜像示例；docker/.dockerignore：标准忽略清单。
- k8s/secret-nacos-cred.example.yaml：Nacos 凭据 Secret 示例（请改为 External Secrets 更佳）。

占位符说明：
- <product>、<service>、<env>、<namespace>、<imageRepo>、<port>
- 统一镜像仓：chek-images-cn-beijing.cr.volces.com

使用示例（新服务 mysvc 于 miker-dev）：
1) 复制模板
```bash
cp -r ops-bootstrap/templates/helm miker.repo/charts/mysvc
cp ops-bootstrap/templates/docker/Dockerfile.node miker.repo/Dockerfile
cp ops-bootstrap/templates/docker/.dockerignore miker.repo/.dockerignore
mkdir -p miker.repo/.github/workflows && \
  cp ops-bootstrap/templates/actions/ci-docker-vecr.yml miker.repo/.github/workflows/ci.yml
```
2) 全局替换占位符并提交
```bash
# 按实际修改：<product>=miker <service>=mysvc <namespace>=miker-dev <port>=3000
```
3) 在 infra/GitOps 仓库添加 values 并创建 Argo CD 应用。
