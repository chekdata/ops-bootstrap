#!/usr/bin/env python3
import argparse
import sys
from urllib.parse import urlencode

import requests


def get_token(registry: str, scopes: list[str], username: str, password: str) -> str:
    params = [("service", "harbor-registry")] + [("scope", s) for s in scopes]
    url = f"https://{registry}/service/token?{urlencode(params)}"
    r = requests.get(url, auth=(username, password))
    if r.status_code != 200:
        raise SystemExit(f"token failed {r.status_code}: {r.text[:300]}")
    data = r.json()
    return data.get("token") or data.get("access_token") or ""


def api(session: requests.Session, method: str, url: str, **kwargs) -> requests.Response:
    r = session.request(method, url, **kwargs)
    if r.status_code in (200, 201, 202):
        return r
    raise SystemExit(f"{method} {url} -> {r.status_code}: {r.text[:300]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", required=True)
    ap.add_argument("--src", required=True, help="source repo:tag, e.g. prod/vehicle-model-service:dev-latest")
    ap.add_argument("--dst", required=True, help="dest repo:tag, e.g. dev/vehicle-model-service:dev-latest")
    ap.add_argument("--username", required=True)
    ap.add_argument("--password", required=True)
    args = ap.parse_args()

    if ":" not in args.src or ":" not in args.dst:
        raise SystemExit("src/dst must include :tag")
    src_repo, src_ref = args.src.split(":", 1)
    dst_repo, dst_ref = args.dst.split(":", 1)

    base = f"https://{args.registry}/v2"
    scopes = [f"repository:{src_repo}:pull", f"repository:{dst_repo}:pull,push"]
    token = get_token(args.registry, scopes, args.username, args.password)
    sess = requests.Session()
    sess.headers.update({
        "Authorization": f"Bearer {token}",
        "Accept": ", ".join([
            "application/vnd.docker.distribution.manifest.v2+json",
            "application/vnd.docker.distribution.manifest.list.v2+json",
            "application/vnd.oci.image.index.v1+json",
            "application/vnd.oci.image.manifest.v1+json",
        ]),
    })

    # GET source manifest
    man_url = f"{base}/{src_repo}/manifests/{src_ref}"
    man = api(sess, "GET", man_url)
    media = man.headers.get("Content-Type", "application/vnd.docker.distribution.manifest.v2+json")
    m = man.json()

    same_repo = (src_repo == dst_repo)

    # If source and destination are the same repository, all blobs/manifests already exist.
    # We can directly PUT the top-level manifest to create a new tag without pushing children.
    if same_repo:
        put = sess.put(f"{base}/{dst_repo}/manifests/{dst_ref}", data=man.content, headers={"Content-Type": media})
        if put.status_code not in (201, 202):
            raise SystemExit(f"PUT manifest failed {put.status_code}: {put.text[:200]}")
        print("OK: copied", args.src, "->", args.dst)
        return

    def ensure_blob(digest: str):
        if same_repo:
            # Blob already exists in the same repo
            return
        mount_url = f"{base}/{dst_repo}/blobs/uploads/?mount={digest}&from={src_repo}"
        r = sess.post(mount_url)
        if r.status_code in (201, 202):
            return
        head = sess.head(f"{base}/{dst_repo}/blobs/{digest}")
        if head.status_code != 200:
            raise SystemExit(f"blob {digest} not present and mount failed {r.status_code}: {r.text[:200]}")

    if media.startswith("application/vnd.docker.distribution.manifest.list.v2+json") or media.startswith("application/vnd.oci.image.index.v1+json"):
        for desc in m.get("manifests", []):
            child_ref = desc.get("digest")
            cm = api(sess, "GET", f"{base}/{src_repo}/manifests/{child_ref}")
            cmedia = cm.headers.get("Content-Type", "application/vnd.docker.distribution.manifest.v2+json")
            if not cmedia.startswith("application/vnd.docker.distribution.manifest.v2+json"):
                # allow OCI manifest too
                if not cmedia.startswith("application/vnd.oci.image.manifest.v1+json"):
                    continue
            child = cm.json()
            cfg = (child.get("config") or {}).get("digest")
            if cfg:
                ensure_blob(cfg)
            for lyr in child.get("layers", []):
                dg = lyr.get("digest")
                if dg:
                    ensure_blob(dg)
            # push child manifest into destination by digest reference
            put_child = sess.put(f"{base}/{dst_repo}/manifests/{child_ref}", data=cm.content, headers={"Content-Type": cmedia})
            if put_child.status_code not in (201, 202):
                raise SystemExit(f"PUT child manifest failed {put_child.status_code}: {put_child.text[:200]}")
    else:
        cfg = (m.get("config") or {}).get("digest")
        if cfg:
            ensure_blob(cfg)
        for lyr in m.get("layers", []):
            dg = lyr.get("digest")
            if dg:
                ensure_blob(dg)

    put = sess.put(f"{base}/{dst_repo}/manifests/{dst_ref}", data=man.content, headers={"Content-Type": media})
    if put.status_code not in (201, 202):
        raise SystemExit(f"PUT manifest failed {put.status_code}: {put.text[:200]}")
    print("OK: copied", args.src, "->", args.dst)


if __name__ == "__main__":
    main()


