# 模板使用说明（复制→替换占位符→提交）

目录结构（已在 miker‑prod 实战验证）：

- actions/ci-docker-vecr.yml：通用 GitHub Actions，构建并推镜像到 VECR（Verified 2025‑10‑20，miker‑prod）。
- actions/k8s-secret-check/：复用的 Secret 完整性检查 Composite Action（校验必需键是否存在）。
- actions/vecr-mirror.yml：镜像从 Docker Hub/GHCR → VECR 的工作流模板（含 summerwind/actions‑runner）（Verified 2025‑10‑20）。
- actions/feishu-notify/：复用的飞书通知 Composite Action（卡片/纯文本两种，Verified 2025‑10‑20）。
- actions/feishu-notify-app.yml：工作流模板（使用应用凭证+chat_id 直接发消息，Verified 2025‑10‑22）。
- helm/：通用 Helm Chart（Deployment/Service/Ingress/values）（Verified 2025‑10‑23）。
  - 端口规范：Service 端口命名 `http`，`targetPort` 缺省指向 `containerPort`（默认 3000）。Ingress backend 使用 `port.name: http`，避免 502。
  - 已在 miker‑prod 实战验证包含 Ingress 命名端口、Service targetPort=容器端口、命名空间与 labels 选择器一致性，避免 503/502。
- docker/Dockerfile.node：Node.js/Next.js 生产镜像示例；docker/.dockerignore：标准忽略清单（Verified 2025‑10‑20）。
- k8s/secret-nacos-cred.example.yaml：Nacos 凭据 Secret 示例（建议改 External Secrets）。
- k8s/arc-runnerdeployment.yaml：ARC RunnerDeployment 模板（summerwind wrapper，VECR 镜像，Verified 2025‑10‑20）。
- k8s/coredns-vecr.yaml：CoreDNS 以 VECR 镜像安装的模板（Verified 2025‑10‑20）。

在 Helm 应用中接入 Nacos（示例）:
```yaml
# values.yaml
nacos:
  enabled: true
  secretRef: nacos-cred   # 包含 address/username/password 三个键
  namespace: miker-prod
```
模板自动把 `nacos-cred` 中的 address 渲染到 `spring.cloud.nacos.*.server-addr`，并把 `username/password` 注入容器环境变量。

占位符说明：
- <product>、<service>、<env>、<namespace>、<imageRepo>、<port>
- 统一镜像仓：chek-images-cn-beijing.cr.volces.com
 - 端口：容器默认 3000；Service 默认 80→targetPort 3000；Ingress backend 使用 `name: http`

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

Secret 完整性自检（示例）：
```yaml
name: check-secrets
on: [workflow_dispatch]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - name: Secret keys check (nacos-cred)
        uses: ./templates/actions/k8s-secret-check
        with:
          kubeconfig: ${{ secrets.KUBECONFIG_B64 }}
          namespace: miker-prod
          secret: nacos-cred
          required-keys: username,password,address,server_addr
```

镜像同步（可选，示例）：
```yaml
# .github/workflows/vecr-mirror.yml
name: vecr-mirror
on:
  workflow_dispatch:
    inputs:
      summerwind_tag:
        description: tag for summerwind/actions-runner
        required: true
        default: latest
jobs:
  mirror:
    runs-on: ubuntu-latest
    steps:
      - name: Login VECR
        env:
          REGISTRY_ENDPOINT: ${{ secrets.REGISTRY_ENDPOINT }}
          REGISTRY_USERNAME: ${{ secrets.REGISTRY_USERNAME }}
          REGISTRY_PASSWORD: ${{ secrets.REGISTRY_PASSWORD }}
        run: echo "$REGISTRY_PASSWORD" | docker login "$REGISTRY_ENDPOINT" -u "$REGISTRY_USERNAME" --password-stdin
      - name: Login DockerHub (optional)
        env:
          DOCKERHUB_USERNAME: ${{ secrets.DOCKERHUB_USERNAME }}
          DOCKERHUB_TOKEN: ${{ secrets.DOCKERHUB_TOKEN }}
        run: |
          if [ -n "$DOCKERHUB_USERNAME" ] && [ -n "$DOCKERHUB_TOKEN" ]; then
            echo "$DOCKERHUB_TOKEN" | docker login docker.io -u "$DOCKERHUB_USERNAME" --password-stdin
          fi
      - name: Mirror summerwind/actions-runner
        env:
          TAG: ${{ github.event.inputs.summerwind_tag }}
          REGISTRY_ENDPOINT: ${{ secrets.REGISTRY_ENDPOINT }}
        run: |
          SRC="docker.io/summerwind/actions-runner:${TAG}"
          DST="${REGISTRY_ENDPOINT}/devops/summerwind-actions-runner:${TAG}"
          docker pull "$SRC"
          docker tag "$SRC" "$DST"
          docker push "$DST"
```

飞书通知（复用 Composite Action）：
```yaml
- name: Notify Feishu
  if: always()
  uses: ./templates/actions/feishu-notify
  with:
    webhook: ${{ secrets.FEISHU_WEBHOOK }}
    title: "${{ github.workflow }} - ${{ job.status }}"
    text: "repo=${{ github.repository }} run=${{ github.run_id }} commit=${{ github.sha }}"
```
注意事项：
- 飞书群通知使用应用凭证时，`content` 必须是卡片 JSON 的字符串（不是对象）；群 `chat_id` 必须有效且应用在群内（形如 `oc_...`）。
- 若组织策略限制外部 actions，优先使用稳定版本：`docker/login-action@v3`、`docker/setup-buildx-action@v3`、`docker/build-push-action@v6`。
- Helm Service 必须命名端口 `http` 并确保 `targetPort` 指向容器端口，Ingress backend 使用 `port.name: http`。
