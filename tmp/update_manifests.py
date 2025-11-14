#!/usr/bin/env python3
import os
import re
import json
import argparse
from pathlib import Path
from typing import List


def parse_args():
    parser = argparse.ArgumentParser(description="Update k8s manifests with new container image")
    parser.add_argument("--app", dest="app", help="Application name (e.g., frontend-app)", default=os.environ.get("APP", "").strip())
    parser.add_argument("--image-repo", dest="image_repo", help="Image repository prefix", default=os.environ.get("IMAGE_REPO", "").strip())
    parser.add_argument("--image-tag", dest="image_tag", help="Image tag", default=os.environ.get("IMAGE_TAG", "").strip())
    parser.add_argument("--image-digest", dest="image_digest", help="Image digest (sha256...)", default=os.environ.get("IMAGE_DIGEST", "").strip())
    parser.add_argument("--envs", dest="envs", help="Comma-separated envs (e.g., dev,staging,prod)", default=os.environ.get("ENVS", "").strip())
    args = parser.parse_args()
    return args


def ensure_required(app: str, image_repo: str, envs: List[str]) -> None:
    if not app or not image_repo or not envs:
        raise SystemExit("Missing APP/IMAGE_REPO/ENVS")


def target_dirs(app: str, envs: List[str]) -> List[Path]:
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


def replace_images_in_file(path: Path, repo_prefix: str, new_image: str) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return False
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


def main():
    args = parse_args()
    app = args.app
    image_repo = args.image_repo
    image_tag = args.image_tag
    image_digest = args.image_digest
    envs = [e.strip() for e in args.envs.split(",") if e.strip()]

    ensure_required(app, image_repo, envs)
    new_image = build_new_image(image_repo, image_tag, image_digest)

    changed = 0
    for root in target_dirs(app, envs):
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.suffix in (".yaml", ".yml"):
                if replace_images_in_file(p, image_repo, new_image):
                    changed += 1
            elif p.suffix == ".json":
                if replace_images_in_json_file(p, image_repo, new_image):
                    changed += 1

    # Write summary for GitHub Actions step consumption
    try:
        Path("/tmp/files_updated.txt").write_text(str(changed), encoding="utf-8")
    except Exception:
        pass

    print(f"TOTAL_FILES_UPDATED {changed}")
    if changed == 0:
        print("WARNING: No files updated. Check IMAGE_REPO/APP/ENVS mapping.")


if __name__ == "__main__":
    main()

