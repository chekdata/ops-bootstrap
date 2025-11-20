# Proposals / 变更提案归档

本目录用于存放已经实施或历史参考性质的变更提案与 patch（例如某次对 Nacos、网关路由的集中调整）。

- `osm-gateway-nacos-env-patch.yaml`：针对 `osm-gateway` 的 Nacos 环境配置补丁示例，可作为后续类似变更的参考。

约定：
- 新的集中性变更（尤其是跨仓/跨环境的 Nacos/Ingress/ALB 等修改），建议在这里落一份 patch + 简要说明，变更实施后再在运维/研发文档中补充最终规范。
- 生产环境的“真源”仍应在对应的 infra 仓或应用仓中，通过 GitOps/Helm/Kustomize 维护；本目录仅作历史与参考归档。


