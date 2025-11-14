#!/usr/bin/env python3
import os, sys, json, urllib.request, http.cookiejar

YAPI = os.environ.get("YAPI_URL", "https://yapi.chekkk.com")
EMAIL = os.environ.get("YAPI_EMAIL", "id@chekkk.com")
PASS  = os.environ.get("YAPI_PASS", "Chek00001")
PID   = int(os.environ.get("YAPI_PID", "68"))

def request_json(url, data=None, headers=None, opener=None):
    if headers is None: headers = {}
    if data is not None and isinstance(data, dict):
        data = json.dumps(data).encode()
        headers.setdefault("Content-Type","application/json")
    req = urllib.request.Request(url, data=data, headers=headers)
    with (opener or urllib.request.build_opener()).open(req, timeout=30) as resp:
        b = resp.read()
        try:
            return json.loads(b.decode())
        except Exception:
            return {}

def main():
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    login = request_json(f"{YAPI}/api/user/login", data={"email": EMAIL, "password": PASS}, opener=opener)
    if login.get("errcode") != 0:
        print("login_failed")
        return
    # fetch project meta
    proj = request_json(f"{YAPI}/api/project/get?id={PID}", opener=opener)
    name = (proj.get("data") or {}).get("name", "")
    basepath = (proj.get("data") or {}).get("basepath", "")
    # list all interfaces (paged)
    page, limit = 1, 200
    interfaces = []
    while True:
        li = request_json(f"{YAPI}/api/interface/list?page={page}&limit={limit}&project_id={PID}", opener=opener)
        arr = li.get("data", {}).get("list", [])
        if not arr: break
        interfaces.extend(arr)
        if len(arr) < limit: break
        page += 1

    total = len(interfaces)
    with_desc = sum(1 for it in interfaces if (it.get("desc") or "").strip())
    with_req_example = 0
    with_resp_example = 0
    tags_total = 0
    for it in interfaces:
        if (it.get("req_body_other") or "").strip():
            with_req_example += 1
        if (it.get("res_body") or "").strip():
            with_resp_example += 1
        tags_total += len(it.get("tag", []) or [])
    avg_tags = (tags_total / total) if total else 0.0

    print(json.dumps({
        "project": {"id": PID, "name": name, "basepath": basepath},
        "total_interfaces": total,
        "with_desc": with_desc,
        "with_req_example": with_req_example,
        "with_resp_example": with_resp_example,
        "avg_tags_per_interface": round(avg_tags, 2)
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()


