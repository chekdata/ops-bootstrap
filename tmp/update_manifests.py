#!/usr/bin/env python3
import os
import re
import json
from pathlib import Path

APP = os.environ.get("APP", "").strip()
IMAGE_REPO = os.environ.get("IMAGE_REPO", "").strip()
IMAGE_TAG = os.environ.get("IMAGE_TAG", "").strip()
IMAGE_DIGEST = os.environ.get("IMAGE_DIGEST", "").strip()
ENVS = [e.strip() for e in os.environ.get("ENVS", "").split(",") if e.strip()]

if not APP or not IMAGE_REPO or not ENVS:
    raise SystemExit("Missing APP/IMAGE_REPO/ENVS")

def target_dirs(app: str, envs: list[str]) -> list[Path]:
    roots = []
    if app == "frontend-saas":
        mapping = {
            "dev": "frontend-saas-dev",
            "staging": "frontend-saas-staging",
            "prod": "frontend-saas-prod",
        }
    elif app == "frontend-app":
        mapping = {
            "dev": "frontend-app-dev",
            "staging": "frontend-app-staging",
            "prod": "frontend-app-prod",
        }
    elif app == "yapi":
        mapping = {
            "prod": "platform/yapi-prod",
        }
    else:
        mapping = {}
    for e in envs:
        d = mapping.get(e)
        if d:
            roots.append(Path(d))
    return roots

def build_new_image(repo: str, tag: str, digest: str) -> str:
    if digest:
        if not digest.startswith("sha256:"):
            digest = f"sha256:{digest}"
        return f"{repo}@{digest}"
    if tag:
        return f"{repo}:{tag}"
    raise SystemExit("IMAGE_TAG or IMAGE_DIGEST required")

NEW_IMAGE = build_new_image(IMAGE_REPO, IMAGE_TAG, IMAGE_DIGEST)

def replace_images_in_file(path: Path, repo_prefix: str, new_image: str) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return False
    # Match lines like: image: repo[:tag]|@sha256:...
    pattern = re.compile(rf'(^\s*image:\s*)(?P<img>{re.escape(repo_prefix)}[^\s"]*)', re.MULTILINE)
    if not pattern.search(text):
        return False
    new_text = pattern.sub(rf'\1{new_image}', text)
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        print(f"UPDATED {path}")
        return True
    return False

def replace_images_in_json_file(path: Path, repo_prefix: str, new_image: str) -> bool:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    if not isinstance(obj, dict):
        return False
    kind = obj.get("kind")
    if kind != "Deployment":
        return False
    spec = obj.get("spec") or {}
    tpl = (spec.get("template") or {}).get("spec") or {}
    containers = tpl.get("containers") or []
    changed = False
    for c in containers:
        img = c.get("image", "")
        if img.startswith(repo_prefix):
            c["image"] = new_image
            changed = True
    if changed:
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"UPDATED_JSON {path}")
        return True
    return False

changed = 0
for root in target_dirs(APP, ENVS):
    if not root.exists():
        continue
for p in root.rglob("*"):
    if p.suffix in (".yaml", ".yml"):
        if replace_images_in_file(p, IMAGE_REPO, NEW_IMAGE):
            changed += 1
    elif p.suffix == ".json":
        if replace_images_in_json_file(p, IMAGE_REPO, NEW_IMAGE):
            changed += 1

print(f"TOTAL_FILES_UPDATED {changed}")
if changed == 0:
    # Not fatal; manifests may not include this image yet
    print("WARNING: No files updated. Check IMAGE_REPO/APP/ENVS mapping.")





