#!/usr/bin/env python3
import os, sys, json, urllib.request
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any

from volcengine.Credentials import Credentials
from volcengine.base.Request import Request
from volcengine.auth.SignerV4 import SignerV4


@dataclass
class AlbEnv:
    name: str
    alb_id: str


def presign(region: str, ak: str, sk: str, action: str, **query) -> str:
    ep = f"alb.{region}.volcengineapi.com"
    req = Request()
    req.method = "GET"
    req.host = ep
    req.path = "/"
    q = {"Action": action, "Version": "2020-04-01", "Region": region}
    q.update(query)
    req.query = q
    req.headers = {"Host": ep}
    cred = Credentials(ak, sk, service="alb", region=region)
    return f"https://{ep}/?" + SignerV4.sign_url(req, cred)


def http_get_json(url: str) -> Dict[str, Any]:
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode())


def list_listeners(region: str, ak: str, sk: str, alb_id: str) -> List[Dict[str, Any]]:
    url = presign(region, ak, sk, "DescribeListeners", LoadBalancerId=alb_id)
    data = http_get_json(url)
    return data.get("Result", {}).get("Listeners", []) or []


def list_rules(region: str, ak: str, sk: str, listener_id: str) -> List[Dict[str, Any]]:
    url = presign(region, ak, sk, "DescribeRules", ListenerId=listener_id)
    data = http_get_json(url)
    return data.get("Result", {}).get("Rules", []) or []


def list_servers(region: str, ak: str, sk: str, server_group_id: str) -> List[Dict[str, Any]]:
    url = presign(region, ak, sk, "DescribeServers", ServerGroupId=server_group_id)
    data = http_get_json(url)
    return data.get("Result", {}).get("Servers", []) or []


def extract_hosts(rule: Dict[str, Any]) -> List[str]:
    values: List[str] = []
    for cond in rule.get("RuleConditions", []) or []:
        if cond.get("Field") == "host-header":
            host_cfg = cond.get("HostConfig") or {}
            vs = host_cfg.get("Values") or []
            for v in vs:
                if isinstance(v, str):
                    values.append(v)
    return values


def extract_forward_group_ids(rule: Dict[str, Any]) -> List[str]:
    ids: List[str] = []
    for act in rule.get("Actions", []) or []:
        if act.get("Type") == "ForwardGroup":
            fg = act.get("ForwardGroupConfig") or {}
            for sg in fg.get("ServerGroups", []) or []:
                sgid = sg.get("ServerGroupId")
                if sgid:
                    ids.append(sgid)
    return ids


def summarize_env(region: str, ak: str, sk: str, env: AlbEnv, hosts: List[str]) -> Dict[str, Any]:
    listeners = list_listeners(region, ak, sk, env.alb_id)
    by_port: Dict[int, List[Dict[str, Any]]] = {}
    for l in listeners:
        by_port.setdefault(int(l.get("Port", 0)), []).append(l)
    result: Dict[str, Any] = {"env": env.name, "alb_id": env.alb_id, "hosts": {}, "listeners": {"80": {}, "443": {}}}
    # index listeners' host conditions
    for port in (80, 443):
        for l in by_port.get(port, []):
            lid = l.get("ListenerId")
            rules = list_rules(region, ak, sk, lid)
            host_values: List[str] = []
            for r in rules:
                host_values.extend(extract_hosts(r))
            result["listeners"][str(port)][lid] = {"rules": len(rules), "hosts": sorted(list(set(host_values)))}
    for host in hosts:
        host = host.strip()
        if not host:
            continue
        hsum: Dict[str, Any] = {"80": {}, "443": {}}
        for port in (80, 443):
            rules_sum = {"listener": None, "rules": 0, "server_groups": [], "healthy_targets": {}}
            for l in by_port.get(port, []):
                lid = l.get("ListenerId")
                rules = list_rules(region, ak, sk, lid)
                matched = [r for r in rules if host in extract_hosts(r)]
                if not matched:
                    continue
                rules_sum["listener"] = lid
                rules_sum["rules"] += len(matched)
                for r in matched:
                    sgids = extract_forward_group_ids(r)
                    for sgid in sgids:
                        if sgid not in rules_sum["server_groups"]:
                            rules_sum["server_groups"].append(sgid)
            # health
            for sgid in rules_sum["server_groups"]:
                srv = list_servers(region, ak, sk, sgid)
                healthy = sum(1 for s in srv if s.get("Status") == "Healthy")
                rules_sum["healthy_targets"][sgid] = healthy
            hsum[str(port)] = rules_sum
        result["hosts"][host] = hsum
    return result


def main():
    ak = os.environ.get("VE_AK") or os.environ.get("AK") or ""
    sk = os.environ.get("VE_SK") or os.environ.get("SK") or ""
    region = os.environ.get("VE_REGION", "cn-beijing")
    hosts_env = os.environ.get("HOSTS", "")
    if not ak or not sk or not hosts_env:
        print("Missing VE_AK/VE_SK/HOSTS", file=sys.stderr)
        sys.exit(2)
    hosts = [h.strip() for h in hosts_env.split(",") if h.strip()]
    envs = [
        AlbEnv("prod", os.environ.get("ALB_PROD", "")),
        AlbEnv("staging", os.environ.get("ALB_STAGING", "")),
        AlbEnv("dev", os.environ.get("ALB_DEV", "")),
    ]
    envs = [e for e in envs if e.alb_id]
    out: Dict[str, Any] = {}
    for e in envs:
        out[e.name] = summarize_env(region, ak, sk, e, hosts)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


