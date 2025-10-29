#!/usr/bin/env python3
import sys
import json
import time
import argparse
from typing import Optional

import requests


def harbor_request(session: requests.Session, base: str, method: str, path: str,
                   expected: tuple = (200,), **kwargs) -> requests.Response:
    url = base.rstrip("/") + path
    resp = session.request(method=method.upper(), url=url, **kwargs)
    if resp.status_code not in expected:
        raise SystemExit(f"{method} {path} -> {resp.status_code}: {resp.text[:500]}")
    return resp


def ensure_project(session: requests.Session, base: str, project: str) -> None:
    r = harbor_request(session, base, "GET", f"/projects?name={project}")
    arr = r.json()
    if isinstance(arr, list) and any(p.get("name") == project for p in arr):
        print(f"Project exists: {project}")
        return
    print(f"Creating project: {project}")
    harbor_request(
        session,
        base,
        "POST",
        "/projects",
        expected=(201,),
        json={"project_name": project, "metadata": {"public": "false"}},
    )
    print(f"Created project: {project}")


def add_member_developer(session: requests.Session, base: str, project: str, username: str) -> None:
    # role_id: 1=projectAdmin, 2=developer, 3=guest, 4=maintainer (varies by Harbor version)
    payload = {"role_id": 2, "member_user": {"username": username}}
    # Ignore if already exists or not a local user (Harbor may return 404/409)
    try:
        r = session.post(base.rstrip("/") + f"/projects/{project}/members", json=payload)
        if r.status_code in (201, 200):
            print(f"Granted developer role to {username} on project {project}")
        else:
            print(f"Skip grant member (status {r.status_code}): {r.text[:200]}")
    except Exception as e:
        print(f"Skip grant member due to error: {e}")


def copy_artifact(session: requests.Session, base: str, src_project: str, src_repo: str, src_ref: str,
                  dst_project: str, dst_repo: str, dst_ref: str) -> None:
    # Harbor copy API: POST /projects/{project}/repositories/{repository}/artifacts?from={project}/{repo}:{ref}
    frm = f"{src_project}/{src_repo}:{src_ref}"
    path = f"/projects/{dst_project}/repositories/{dst_repo}/artifacts?from={frm}"
    r = session.post(base.rstrip("/") + path)
    if r.status_code in (201, 202):
        print(f"Copy requested: {frm} -> {dst_project}/{dst_repo}:{dst_ref}")
    elif r.status_code == 409:
        print("Artifact already exists at destination (409)")
    else:
        raise SystemExit(f"Copy artifact failed {r.status_code}: {r.text[:300]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", required=True, help="VECR host, e.g. chek-images-cn-beijing.cr.volces.com")
    ap.add_argument("--user", required=True, help="VECR username")
    ap.add_argument("--password", required=True, help="VECR password")
    ap.add_argument("--ensure-project", default="dev", help="Project name to ensure exists (default: dev)")
    ap.add_argument("--grant-user", default=None, help="Username to grant developer role on project")
    ap.add_argument("--copy-from", default=None, help="Copy from <project/repo:ref> (e.g. prod/vehicle-model-service:dev-latest)")
    ap.add_argument("--copy-to", default=None, help="Copy to <project/repo:ref> (e.g. dev/vehicle-model-service:dev-latest)")
    args = ap.parse_args()

    base = f"https://{args.registry}/api/v2.0"
    sess = requests.Session()
    sess.auth = (args.user, args.password)
    sess.headers.update({"Accept": "application/json"})

    # Sanity check API reachable
    harbor_request(sess, base, "GET", "/projects", expected=(200,))

    # Ensure project
    ensure_project(sess, base, args.ensure_project)

    if args.grant_user:
        add_member_developer(sess, base, args.ensure_project, args.grant_user)

    if args.copy_from and args.copy_to:
        def split_ref(s: str):
            # format: project/repo:ref
            proj_repo, ref = s.split(":", 1)
            proj, repo = proj_repo.split("/", 1)
            return proj, repo, ref

        sp, sr, sref = split_ref(args.copy_from)
        dp, dr, dref = split_ref(args.copy_to)
        copy_artifact(sess, base, sp, sr, sref, dp, dr, dref)

    print("Done")


if __name__ == "__main__":
    main()





