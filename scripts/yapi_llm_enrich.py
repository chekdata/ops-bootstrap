#!/usr/bin/env python3
import os
import sys
import json
import time
import urllib.parse
import urllib.request
from typing import Dict, Any

"""
Usage:
  env:
    LLM_API_KEY=sk-...
    LLM_ENDPOINT=https://api.openai.com/v1
    LLM_MODEL=gpt-4o-mini
    YAPI_URL=https://yapi.chekkk.com
    YAPI_TOKEN_DEV=...
    YAPI_TOKEN_STG=...
    YAPI_TOKEN_PROD=...
  args:
    scripts/yapi_llm_enrich.py /path/to/swagger.json
"""


def http_post_json(url: str, data: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode("utf-8", "ignore")
        try:
            return json.loads(raw)
        except Exception:
            return {"_raw": raw}


def http_post_form(url: str, form: Dict[str, str]) -> Dict[str, Any]:
    data = urllib.parse.urlencode(form).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode("utf-8", "ignore")
        try:
            return json.loads(raw)
        except Exception:
            return {"_raw": raw}


def llm_enrich_description(api_key: str, endpoint: str, model: str, op: Dict[str, Any], path: str, method: str) -> str:
    summary = op.get("summary") or ""
    desc = (op.get("description") or "").strip()
    if len(desc) >= 50:
        return desc  # keep existing rich description

    sys_prompt = "你是资深后端与文档工程师。请用简体中文为接口补充简洁而信息量高的说明，包含用途、入参要点、典型用法示例。限制在 150-220 字。"
    user_prompt = {
        "path": path,
        "method": method.upper(),
        "summary": summary,
        "params_hint": [
            {"in": p.get("in"), "name": p.get("name"), "required": p.get("required")} for p in op.get("parameters", []) or []
        ]
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)}
        ],
        "temperature": 0.2,
        "max_tokens": 300
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    try:
        resp = http_post_json(f"{endpoint.rstrip('/')}/chat/completions", payload, headers)
        content = (((resp or {}).get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        return content.strip() or desc
    except Exception:
        return desc


def enrich_swagger(swagger: Dict[str, Any], api_key: str, endpoint: str, model: str) -> Dict[str, Any]:
    paths = swagger.get("paths") or {}
    for path, methods in paths.items():
        for method, op in (methods or {}).items():
            if not isinstance(op, dict):
                continue
            new_desc = llm_enrich_description(api_key, endpoint, model, op, path, method)
            if new_desc and new_desc != op.get("description"):
                op["description"] = new_desc
            # small sleep to avoid throttling
            time.sleep(0.2)
    return swagger


def import_to_yapi(yapi_url: str, token: str, swagger_json_path: str) -> Dict[str, Any]:
    # Use open import API with local file content
    with open(swagger_json_path, "r", encoding="utf-8") as f:
        content = f.read()
    form = {
        "type": "swagger",
        "merge": "1",
        "token": token,
        "json": content
    }
    return http_post_form(f"{yapi_url.rstrip('/')}/api/open/import_data", form)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: scripts/yapi_llm_enrich.py /path/to/swagger.json", file=sys.stderr)
        return 2
    source = sys.argv[1]
    if not os.path.exists(source):
        print(f"not found: {source}", file=sys.stderr)
        return 2

    yapi_url = os.getenv("YAPI_URL", "https://yapi.chekkk.com")
    api_key = os.getenv("LLM_API_KEY", "")
    endpoint = os.getenv("LLM_ENDPOINT", "https://api.openai.com/v1")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    if not api_key:
        print("LLM_API_KEY is required", file=sys.stderr)
        return 2

    with open(source, "r", encoding="utf-8") as f:
        swagger = json.load(f)

    enriched = enrich_swagger(swagger, api_key, endpoint, model)
    out_path = "/tmp/swagger_enriched.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, separators=(",", ":"))
    print(json.dumps({"enriched_path": out_path}, ensure_ascii=False))

    results = {}
    for name, env_var in [("DEV", "YAPI_TOKEN_DEV"), ("STG", "YAPI_TOKEN_STG"), ("PROD", "YAPI_TOKEN_PROD")]:
        token = os.getenv(env_var, "").strip()
        if not token:
            continue
        try:
            res = import_to_yapi(yapi_url, token, out_path)
            results[name] = res
        except Exception as e:
            results[name] = {"err": str(e)}
    print(json.dumps({"import_results": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



