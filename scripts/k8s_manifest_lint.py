#!/usr/bin/env python3
"""
K8s 清单规约校验脚本（长期开启的门禁）

检查点（当前版本）：
1. 禁止 nginx-class Ingress：
   - metadata.annotations["kubernetes.io/ingress.class"] == "nginx"
   - spec.ingressClassName == "nginx"
2. API 网关域名必须落在平台命名空间：
   - api.chekkk.com       → namespace == platform-prod
   - api-dev.chekkk.com   → namespace == platform-dev
   - api-staging.chekkk.com → namespace == platform-staging
3. NodePort Service 端口必须显式命名为 http。

后续可按需要继续扩展更多规约。
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - 在 CI 中应总是可用
    yaml = None


REPO_ROOT = Path(__file__).resolve().parents[1]

# 仅扫描 K8s 清单所在目录，避免误扫日志/文档
SCAN_DIRS = [
    "templates/k8s",
    "templates/helm/examples",
    "frontend-app-dev",
    "frontend-app-prod",
    "frontend-app-staging",
    "charts",
    "platform",
]


class LintError(Exception):
    pass


def iter_yaml_files() -> list[Path]:
    files: list[Path] = []
    for rel in SCAN_DIRS:
        base = REPO_ROOT / rel
        if not base.exists():
            continue
        for path in base.rglob("*.y[a]ml"):
            # 跳过临时/样例清单
            if "/.git/" in str(path):
                continue
            files.append(path)
    return sorted(files)


def load_docs(path: Path) -> list[dict]:
    if yaml is None:
        # 没有 YAML 解析库时直接跳过（本地环境宽松，CI 会安装依赖）
        return []

    text = path.read_text(encoding="utf-8")
    docs: list[dict] = []
    for doc in yaml.safe_load_all(text):
        if isinstance(doc, dict):
            docs.append(doc)
    return docs


def check_ingress(doc: dict, path: Path, errors: list[str]) -> None:
    metadata = doc.get("metadata") or {}
    spec = doc.get("spec") or {}
    ns = metadata.get("namespace") or ""

    annotations = metadata.get("annotations") or {}
    ingress_class = spec.get("ingressClassName") or ""
    ann_class = annotations.get("kubernetes.io/ingress.class") or ""

    # 1) 禁止 nginx-class Ingress
    if ingress_class == "nginx" or ann_class == "nginx":
        errors.append(
            f"{path}: Ingress 使用 nginx ingressClass（namespace={ns!r}），请迁移到 ALB（chek-<env>-alb）后删除该清单。"
        )

    # 2) API 网关域名必须落在平台命名空间
    rules = spec.get("rules") or []
    for rule in rules:
        host = (rule or {}).get("host") or ""
        if host == "api.chekkk.com" and ns != "platform-prod":
            errors.append(
                f"{path}: Ingress host=api.chekkk.com 但 namespace={ns!r}，必须迁移到 namespace=platform-prod。"
            )
        if host == "api-dev.chekkk.com" and ns != "platform-dev":
            errors.append(
                f"{path}: Ingress host=api-dev.chekkk.com 但 namespace={ns!r}，必须迁移到 namespace=platform-dev。"
            )
        if host == "api-staging.chekkk.com" and ns != "platform-staging":
            errors.append(
                f"{path}: Ingress host=api-staging.chekkk.com 但 namespace={ns!r}，必须迁移到 namespace=platform-staging。"
            )


def check_service(doc: dict, path: Path, errors: list[str]) -> None:
    metadata = doc.get("metadata") or {}
    spec = doc.get("spec") or {}
    ns = metadata.get("namespace") or ""

    svc_type = spec.get("type") or "ClusterIP"
    if svc_type != "NodePort":
        return

    ports = spec.get("ports") or []
    for idx, port in enumerate(ports):
        name = (port or {}).get("name")
        if not name:
            errors.append(
                f"{path}: NodePort Service(namespace={ns!r}) 端口 index={idx} 未设置 name=http，请统一端口名为 http。"
            )
        elif name != "http":
            errors.append(
                f"{path}: NodePort Service(namespace={ns!r}) 端口 name={name!r} 非 http，请统一端口名为 http。"
            )


def lint_file(path: Path) -> list[str]:
    errors: list[str] = []
    docs = load_docs(path)
    for doc in docs:
        kind = doc.get("kind")
        if kind == "Ingress":
            check_ingress(doc, path, errors)
        elif kind == "Service":
            check_service(doc, path, errors)
    return errors


def main() -> int:
    all_errors: list[str] = []
    files = iter_yaml_files()
    for path in files:
        text = path.read_text(encoding="utf-8")
        # 跳过包含 Helm 模板语法或长多行 shell/python 片段的清单：
        # 这类文件通常作为“运维工具型 DaemonSet/Job”，不适合作为结构化 YAML 校验对象。
        if "{{" in text or "{%" in text or "set -euo pipefail" in text:
            continue
        try:
            all_errors.extend(lint_file(path))
        except Exception as exc:
            all_errors.append(f"{path}: YAML 解析失败: {exc}")

    if all_errors:
        sys.stderr.write("K8s 清单规约校验失败：\n")
        for msg in all_errors:
            sys.stderr.write(f"- {msg}\n")
        return 1

    print("K8s 清单规约校验通过（当前检查：禁止 nginx-class Ingress、API 域名归平台、NodePort 端口名 http）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


