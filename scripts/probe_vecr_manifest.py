#!/usr/bin/env python3
import argparse
import sys
from urllib.parse import urlencode

import requests


def get_token(registry: str, repo: str, username: str, password: str) -> str:
    params = {
        "service": "harbor-registry",
        "scope": f"repository:{repo}:pull",
    }
    url = f"https://{registry}/service/token?{urlencode(params)}"
    resp = requests.get(url, auth=(username, password), timeout=20)
    if resp.status_code != 200:
        print(f"token {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
        return ""
    data = resp.json()
    return data.get("token") or data.get("access_token") or ""


def probe_manifest(registry: str, repo: str, ref: str, token: str) -> int:
    url = f"https://{registry}/v2/{repo}/manifests/{ref}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": ", ".join([
            "application/vnd.docker.distribution.manifest.v2+json",
            "application/vnd.docker.distribution.manifest.list.v2+json",
            "application/vnd.oci.image.index.v1+json",
            "application/vnd.oci.image.manifest.v1+json",
        ]),
    }
    resp = requests.head(url, headers=headers, timeout=20)
    return resp.status_code


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--ref", required=True)
    ap.add_argument("--username", required=True)
    ap.add_argument("--password", required=True)
    args = ap.parse_args()

    token = get_token(args.registry, args.repo, args.username, args.password)
    if not token:
        print("no token", file=sys.stderr)
        sys.exit(3)
    code = probe_manifest(args.registry, args.repo, args.ref, token)
    print(code)
    sys.exit(0 if code == 200 else 2)


if __name__ == "__main__":
    main()





