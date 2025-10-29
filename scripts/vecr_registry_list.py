#!/usr/bin/env python3
import argparse
import json
import sys
from urllib.parse import urlencode

import requests


def get_bearer_token(registry: str, repo: str, username: str, password: str) -> str:
    # Harbor-compatible token endpoint
    params = {
        "service": "harbor-registry",
        "scope": f"repository:{repo}:pull",
    }
    url = f"https://{registry}/service/token?{urlencode(params)}"
    resp = requests.get(url, auth=(username, password))
    if resp.status_code != 200:
        raise SystemExit(f"token request failed {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    token = data.get("token") or data.get("access_token")
    if not token:
        raise SystemExit("no token in response")
    return token


def list_tags(registry: str, repo: str, token: str) -> list:
    url = f"https://{registry}/v2/{repo}/tags/list"
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
    if resp.status_code != 200:
        raise SystemExit(f"list tags failed {resp.status_code}: {resp.text[:300]}")
    obj = resp.json()
    tags = obj.get("tags") or []
    return tags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", required=True)
    ap.add_argument("--repo", required=True, help="e.g. prod/vehicle-model-service")
    ap.add_argument("--username", required=True)
    ap.add_argument("--password", required=True)
    args = ap.parse_args()

    token = get_bearer_token(args.registry, args.repo, args.username, args.password)
    tags = list_tags(args.registry, args.repo, token)
    print(json.dumps({"repo": args.repo, "tags": tags}, ensure_ascii=False))


if __name__ == "__main__":
    main()





