#!/usr/bin/env python3
import os
import sys
import json
from typing import Any, Dict, List

try:
    import volcenginesdkcore
    import volcenginesdkalb
    from volcenginesdkalb.models.describe_listeners_request import DescribeListenersRequest
    from volcenginesdkalb.models.describe_rules_request import DescribeRulesRequest
    from volcenginesdkalb.models.delete_rules_request import DeleteRulesRequest
except Exception as e:
    print("ERROR: missing volcengine SDKs. Please install volcenginesdkcore and volcenginesdkalb.", file=sys.stderr)
    raise


def to_dict(obj: Any) -> Any:
    # Best-effort serialization across SDK versions
    try:
        return obj.to_dict()
    except Exception:
        pass
    try:
        from volcenginesdkcore.api_client import ApiClient
        return ApiClient().sanitize_for_serialization(obj)
    except Exception:
        pass
    try:
        return json.loads(json.dumps(obj, default=lambda o: getattr(o, "__dict__", str(o))))
    except Exception:
        return obj


def get_env(name: str, default: str = "") -> str:
    v = os.environ.get(name, "")
    if not v and default:
        return default
    return v


def main() -> int:
    ak = get_env("AK") or get_env("VOLC_AK")
    sk = get_env("SK") or get_env("VOLC_SK")
    region = get_env("REGION", "cn-beijing")
    alb_id = get_env("ALB_ID")
    host = get_env("HOST", "api.chekkk.com")
    if not (ak and sk and alb_id):
        print("ERROR: missing AK/SK or ALB_ID", file=sys.stderr)
        return 2

    cfg = volcenginesdkcore.Configuration()
    cfg.ak = ak
    cfg.sk = sk
    cfg.region = region
    volcenginesdkcore.Configuration.set_default(cfg)

    api = volcenginesdkalb.ALBApi()

    # 1) Find HTTP:80 listener for this ALB
    lst_req = DescribeListenersRequest(load_balancer_id=alb_id)
    lst_resp = api.describe_listeners(lst_req)
    lst = to_dict(lst_resp)
    listeners = []
    for key in ("listeners", "Listeners", "result", "Result"):
        v = lst.get(key) if isinstance(lst, dict) else None
        if isinstance(v, dict):
            for alt in ("listeners", "Listeners"):
                if isinstance(v.get(alt), list):
                    listeners = v.get(alt)
                    break
        if isinstance(v, list):
            listeners = v
        if listeners:
            break
    if not listeners:
        # some SDKs return directly with top-level list
        if isinstance(lst, list):
            listeners = lst
    if not listeners:
        print("ERROR: no listeners found", file=sys.stderr)
        return 3
    http80 = None
    for it in listeners:
        proto = str(it.get("protocol") or it.get("Protocol") or "").upper()
        port = int(it.get("port") or it.get("Port") or 0)
        if proto == "HTTP" and port == 80:
            http80 = it
            break
    if not http80:
        print("No HTTP:80 listener found; nothing to clean.")
        return 0
    listener_id = http80.get("listener_id") or http80.get("ListenerId")
    if not listener_id:
        print("ERROR: cannot resolve ListenerId", file=sys.stderr)
        return 4

    # 2) Describe rules on 80
    dr_req = DescribeRulesRequest(listener_id=listener_id)
    dr_resp = api.describe_rules(dr_req)
    dr = to_dict(dr_resp)
    rules: List[Dict[str, Any]] = []
    for path in (("result", "rules"), ("Result", "Rules"), ("rules",), ("Rules",)):
        cur = dr
        ok = True
        for k in path:
            if isinstance(cur, dict) and k in cur:
                cur = cur[k]
            else:
                ok = False
                break
        if ok and isinstance(cur, list):
            rules = cur
            break
    if not rules and isinstance(dr, list):
        rules = dr

    # 3) Identify api.chekkk.com business rules to remove from 80
    targets: List[str] = []
    for r in rules:
        rid = r.get("rule_id") or r.get("RuleId")
        if not rid:
            continue
        domain = r.get("domain") or r.get("Domain") or ""
        path = r.get("url") or r.get("Url") or r.get("path") or r.get("Path") or ""
        # Try nested conditions
        if not domain or not path:
            conds = r.get("rule_conditions") or r.get("RuleConditions") or []
            if isinstance(conds, list):
                for c in conds:
                    fld = str(c.get("field") or c.get("Field") or "").lower()
                    if fld in ("host", "host-header", "hostheader"):
                        vals = (c.get("host_header_config") or c.get("HostHeaderConfig") or {}).get("values") or []
                        if vals:
                            domain = domain or vals[0]
                    if fld in ("path", "path-pattern"):
                        cfg = c.get("path_config") or c.get("PathConfig") or c.get("path_pattern_config") or c.get("PathPatternConfig") or {}
                        vals = cfg.get("values") or []
                        if vals:
                            path = path or vals[0]
        if domain == host:
            # On 80 we don't want business paths; remove '/', '/openapi', '/openapi.json', '/api/*'
            if path in ("/", "/openapi", "/openapi.json") or path.startswith("/api/") or path.startswith("/osm-gateway"):
                targets.append(rid)

    if not targets:
        print("No matching HTTP/80 business rules to delete; nothing to do.")
        return 0

    del_req = DeleteRulesRequest(listener_id=listener_id, rule_ids=targets)
    api.delete_rules(del_req)
    print(json.dumps({"deleted_rule_ids": targets}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())



