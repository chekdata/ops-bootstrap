#!/usr/bin/env python3
import os
import sys
from urllib.parse import urlencode

import requests


REGISTRY = "chek-images-cn-beijing.cr.volces.com"
USERNAME = os.environ.get("REGISTRY_USERNAME") or ""
PASSWORD = os.environ.get("REGISTRY_PASSWORD") or ""


def get_token(registry: str, scopes: list[str], username: str, password: str) -> str:
    params = [("service", "harbor-registry")] + [("scope", s) for s in scopes]
    url = f"https://{registry}/service/token?{urlencode(params)}"
    r = requests.get(url, auth=(username, password))
    r.raise_for_status()
    data = r.json()
    return data.get("token") or data.get("access_token") or ""


def api(session: requests.Session, method: str, url: str, **kwargs) -> requests.Response:
    r = session.request(method, url, **kwargs)
    if r.status_code in (200, 201, 202, 202, 204):
        return r
    raise SystemExit(f"{method} {url} -> {r.status_code}: {r.text[:300]}")


def list_tags(sess: requests.Session, repo: str) -> list[str]:
    url = f"https://{REGISTRY}/v2/{repo}/tags/list"
    r = api(sess, "GET", url)
    data = r.json()
    return data.get("tags") or []


def get_manifest_digest(sess: requests.Session, repo: str, tag: str) -> str:
    url = f"https://{REGISTRY}/v2/{repo}/manifests/{tag}"
    r = api(sess, "GET", url, headers={"Accept": "application/vnd.docker.distribution.manifest.v2+json"})
    return r.headers.get("Docker-Content-Digest") or ""


def delete_tag(sess: requests.Session, repo: str, tag: str) -> None:
    digest = get_manifest_digest(sess, repo, tag)
    if not digest:
        print(f"[SKIP] {repo}:{tag} no digest")
        return
    url = f"https://{REGISTRY}/v2/{repo}/manifests/{digest}"
    r = sess.delete(url)
    if r.status_code not in (202, 200, 201, 204):
        raise SystemExit(f"DELETE {url} -> {r.status_code}: {r.text[:300]}")
    print(f"[DEL] {repo}:{tag} ({digest})")


def is_protected(tag: str) -> bool:
    # 按指南保留的固定 / 版本 tag
    if tag in {"dev", "staging", "prod"}:
        return True
    if tag.startswith("v") and len(tag) >= 2:
        return True
    return False


def main():
    if not USERNAME or not PASSWORD:
        raise SystemExit("need REGISTRY_USERNAME and REGISTRY_PASSWORD in env")

    repos = ["dev/backend-saas", "prod/backend-saas"]
    scopes = [f"repository:{r}:pull,push" for r in repos]
    token = get_token(REGISTRY, scopes, USERNAME, PASSWORD)
    sess = requests.Session()
    sess.headers.update({"Authorization": f"Bearer {token}"})

    for repo in repos:
        try:
            tags = list_tags(sess, repo)
        except SystemExit as e:
            print(f"[WARN] skip {repo}: {e}")
            continue
        if not tags:
            print(f"[INFO] {repo}: no tags")
            continue
        print(f"[INFO] {repo} tags: {', '.join(sorted(tags))}")
        for tag in tags:
            if is_protected(tag):
                print(f"[KEEP] {repo}:{tag}")
                continue
            # sha-*、latest、main 等旧标签全部清理
            delete_tag(sess, repo, tag)


if __name__ == "__main__":
    main()


