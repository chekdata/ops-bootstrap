### TOS 私网接入（VPC Endpoint）步骤（cn-beijing）

- 目标：开启 TOS VPC Endpoint，绑定集群子网与安全组，启用私有解析。
- 关键信息：`VpcId=<chek-k8s-vpc-01>`、`SubnetIds=[172.31.120.0/24,172.31.121.0/24]`、`SecurityGroupId=<sg-...>`。
- 控制台步骤：
  1) 创建私有连接（Privatelink）服务：选择 TOS，区域 cn-beijing。
  2) 绑定子网：选择与集群节点相同的子网。
  3) 绑定安全组：放通出站 TCP 443。
  4) 启用私有 DNS：`tos-cn-beijing.volces.com` 解析到 VPC Endpoint。
- 验证：
  - Pod 内 `curl -I https://tos-cn-beijing.volces.com` 延迟应低于公网。
  - 断开节点公网后仍可访问（需保留安全组 443 出站到 Endpoint）。




