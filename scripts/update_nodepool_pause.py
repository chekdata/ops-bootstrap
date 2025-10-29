#!/usr/bin/env python3
import json
import sys
import base64
from typing import Optional

from volcengine.base.Service import Service
from volcengine.ApiInfo import ApiInfo
from volcengine.ServiceInfo import ServiceInfo
from volcengine.Credentials import Credentials


def make_service(ak: str, sk: str, region: str, service: str, host: str = "open.volcengineapi.com") -> Service:
    # Note: Credentials expects (service, region) order in this SDK
    creds = Credentials(ak, sk, service, region)
    svc_info = ServiceInfo(
        host=host,
        header={"Accept": "application/json"},
        credentials=creds,
        connection_timeout=60,
        socket_timeout=60,
        scheme="https",
    )
    api_info = {"Generic": ApiInfo("POST", "/", {}, {}, {})}
    return Service(svc_info, api_info)


def describe_node_pools(svc: Service, cluster_id: str) -> list[dict]:
    params = {"Action": "DescribeNodePools", "Version": "2022-05-12"}
    form = {"ClusterId": cluster_id}
    txt = svc.post("Generic", params, form)
    obj = json.loads(txt)
    result = obj.get("Result", {})
    node_pools = (
        result.get("NodePools")
        or result.get("NodePoolSet")
        or result.get("NodePoolList")
        or []
    )
    return node_pools if isinstance(node_pools, list) else []


def pick_pool_id(pools: list[dict]) -> Optional[str]:
    for p in pools:
        if not isinstance(p, dict):
            continue
        for key in ("Id", "NodePoolId"):
            if key in p and p[key]:
                return p[key]
        nested = p.get("NodePool", {})
        for key in ("Id", "NodePoolId"):
            if key in nested and nested[key]:
                return nested[key]
    return None


def update_pause_image(svc: Service, cluster_id: str, pool_id: str, pause_image: str) -> str:
    # Try dot-notation first
    params = {"Action": "UpdateNodePoolConfig", "Version": "2022-05-12"}
    form = {
        "ClusterId": cluster_id,
        "Id": pool_id,
        "KubernetesConfig.PauseImage": pause_image,
    }
    try:
        return svc.post("Generic", params, form)
    except Exception:
        # Fallback to JSON-encoded nested field
        form2 = {
            "ClusterId": cluster_id,
            "Id": pool_id,
            "KubernetesConfig": json.dumps({"PauseImage": pause_image}, separators=(",", ":")),
        }
        return svc.post("Generic", params, form2)


def main():
    if len(sys.argv) < 5:
        print(
            "Usage: update_nodepool_pause.py <AK> <SK(b64 or plain)> <Region> <ClusterId> [PauseImage]",
            file=sys.stderr,
        )
        sys.exit(2)
    ak = sys.argv[1]
    sk_in = sys.argv[2]
    region = sys.argv[3]
    cluster = sys.argv[4]
    pause = sys.argv[5] if len(sys.argv) > 5 else "registry.aliyuncs.com/google_containers/pause:3.6"
    # decode sk if base64
    try:
        sk = base64.b64decode(sk_in).decode()
    except Exception:
        sk = sk_in

    # Try multiple service/host combinations for KE OpenAPI
    candidates = [
        ("ke", "open.volcengineapi.com"),
        ("ke", "ke.volcengineapi.com"),
        ("eks", "open.volcengineapi.com"),
        ("vke", "open.volcengineapi.com"),
        ("ecs", "open.volcengineapi.com"),
    ]

    last_err = None
    pools = []
    svc = None
    for svc_name, host in candidates:
        try:
            svc = make_service(ak, sk, region, svc_name, host=host)
            pools = describe_node_pools(svc, cluster)
            if pools:
                break
        except Exception as e:
            last_err = e
            continue
    if not pools:
        raise SystemExit(f"DescribeNodePools failed: {last_err}")
    if not pools:
        print("No node pools returned", file=sys.stderr)
        sys.exit(1)
    pool_id = pick_pool_id(pools)
    if not pool_id:
        print("No node pool id found", file=sys.stderr)
        sys.exit(1)
    upd = update_pause_image(svc, cluster, pool_id, pause)
    print(upd)


if __name__ == "__main__":
    main()


