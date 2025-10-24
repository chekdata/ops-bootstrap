#!/usr/bin/env python3
"""
MySQL image/object reference inventory scanner (read-only).

Purpose:
- Discover columns likely storing image/object references (avatar, cover, image, url, object key, path, minio, etc.)
- Sample values to infer whether they are URLs or object keys and identify naming/prefix patterns
- Generate Markdown and CSV reports to aid MinIO → TOS migration planning

Usage:
  python mysql_scan_images.py --host <host> --port 3306 --user <user> --password <password> \
    --output-dir <dir> [--databases db1,db2]

Notes:
- This script performs only read-only metadata queries and limited SELECT samples.
- It excludes system schemas (information_schema, performance_schema, mysql, sys).
"""

import argparse
import csv
import datetime
import os
import re
import sys
from typing import Dict, List, Tuple

try:
    import pymysql
except ImportError as exc:
    print("[ERROR] pymysql is required. Install with: pip install pymysql", file=sys.stderr)
    raise


SYSTEM_SCHEMAS = {"information_schema", "performance_schema", "mysql", "sys"}

COLUMN_KEYWORDS = [
    "avatar", "cover", "image", "logo", "thumb", "thumbnail", "picture", "photo",
    "url", "uri", "object", "key", "path", "file", "filename", "minio", "s3", "oss",
    "endpoint", "bucket", "cdn", "media"
]


def build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inventory image/object-related columns in MySQL.")
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--databases", help="Comma-separated database list to include (optional)")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--sample", type=int, default=5, help="Sample rows per column")
    parser.add_argument("--timeout", type=int, default=10, help="Connection timeout seconds")
    return parser


def open_connection(host: str, port: int, user: str, password: str, db: str = None, timeout: int = 10):
    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=db,
        connect_timeout=timeout,
        read_timeout=timeout,
        write_timeout=timeout,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def list_databases(conn, include: List[str] = None) -> List[str]:
    with conn.cursor() as cur:
        cur.execute("SHOW DATABASES")
        dbs = [row["Database"] for row in cur.fetchall()]
    filtered = [d for d in dbs if d not in SYSTEM_SCHEMAS]
    if include:
        include_set = {d.strip() for d in include}
        filtered = [d for d in filtered if d in include_set]
    return filtered


def find_candidate_columns(conn, db: str) -> List[Dict[str, str]]:
    # Build parameterized LIKE conditions to avoid percent-sign formatting conflicts
    conditions = ["COLUMN_NAME LIKE %s" for _ in COLUMN_KEYWORDS]
    like_clause = " OR ".join(conditions)
    params = [db] + [f"%{kw}%" for kw in COLUMN_KEYWORDS]
    sql = (
        "SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE "
        "FROM information_schema.COLUMNS "
        f"WHERE TABLE_SCHEMA = %s AND ({like_clause}) "
        "ORDER BY TABLE_NAME, ORDINAL_POSITION"
    )
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def sample_column_values(conn, db: str, table: str, column: str, sample: int) -> Tuple[int, List[str]]:
    # Count non-empty
    count_sql = f"SELECT COUNT(1) AS cnt FROM `{db}`.`{table}` WHERE `{column}` IS NOT NULL AND `{column}` <> ''"
    # Sample values (DISTINCT to increase variety; LIMIT to cap IO)
    sample_sql = (
        f"SELECT DISTINCT `{column}` AS v FROM `{db}`.`{table}` "
        f"WHERE `{column}` IS NOT NULL AND `{column}` <> '' LIMIT {sample}"
    )
    with conn.cursor() as cur:
        cur.execute(count_sql)
        total = int(cur.fetchone()["cnt"])
        cur.execute(sample_sql)
        values = [row["v"] for row in cur.fetchall()]
    return total, values


def classify_value(v) -> str:
    # Normalize to string for classification
    if isinstance(v, bytes):
        try:
            v = v.decode("utf-8", errors="ignore")
        except Exception:
            v = str(v)
    elif not isinstance(v, str):
        v = str(v)
    s = v.strip().lower()
    if s.startswith("http://") or s.startswith("https://"):
        if "minio" in s or "s3" in s or ".cos." in s or ".oss-" in s:
            return "url_object_storage"
        return "url"
    if s.startswith("s3://"):
        return "s3_uri"
    if "/" in s and (".jpg" in s or ".jpeg" in s or ".png" in s or ".gif" in s or ".webp" in s):
        return "object_key"
    return "text"


def infer_prefix(values: List[str]) -> str:
    # Attempt to guess a common prefix (directory-like) from samples
    normalized: List[str] = []
    for v in values:
        if isinstance(v, bytes):
            try:
                v = v.decode("utf-8", errors="ignore")
            except Exception:
                v = str(v)
        elif not isinstance(v, str):
            v = str(v)
        normalized.append(v)
    cleaned = [v.strip() for v in normalized if v and v.strip()]
    if not cleaned:
        return ""
    parts_lists = [v.split("/") for v in cleaned]
    common: List[str] = []
    for idx in range(min(len(p) for p in parts_lists)):
        tokens = {p[idx] for p in parts_lists}
        if len(tokens) == 1:
            common.append(tokens.pop())
        else:
            break
    if not common:
        return ""
    return "/".join(common)


def main():
    parser = build_argparser()
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    md_path = os.path.join(args.output_dir, f"mysql_image_inventory_{ts}.md")
    csv_path = os.path.join(args.output_dir, f"mysql_image_inventory_{ts}.csv")

    root_conn = open_connection(args.host, args.port, args.user, args.password, timeout=args.timeout)
    try:
        include_dbs = args.databases.split(",") if args.databases else None
        databases = list_databases(root_conn, include=include_dbs)

        all_rows: List[Dict[str, str]] = []
        md_lines: List[str] = []
        md_lines.append(f"# MySQL Image/Object Inventory\n")
        md_lines.append(f"Host: `{args.host}`  Port: `{args.port}`  Time(UTC): `{ts}`\n")
        md_lines.append(f"Databases scanned: {', '.join(databases) if databases else '(none)'}\n")

        for db in databases:
            md_lines.append(f"\n## Database: `{db}`\n")
            db_conn = open_connection(args.host, args.port, args.user, args.password, db=db, timeout=args.timeout)
            try:
                candidates = find_candidate_columns(db_conn, db)
                if not candidates:
                    md_lines.append("(no candidate columns)\n")
                    continue
                md_lines.append("\n| Table | Column | DataType | NonEmpty | Sample1..N | Classification | InferredPrefix |\n")
                md_lines.append("|---|---|---:|---:|---|---|---|\n")
                for col in candidates:
                    table = col["TABLE_NAME"]
                    column = col["COLUMN_NAME"]
                    dtype = col["DATA_TYPE"]
                    try:
                        total, samples = sample_column_values(db_conn, db, table, column, args.sample)
                    except Exception as e:
                        total, samples = -1, [f"<error: {e.__class__.__name__}>"]

                    # Classify on first sample or majority
                    classes = [classify_value(v) for v in samples]
                    if classes:
                        # majority class
                        cls = max(set(classes), key=classes.count)
                    else:
                        cls = "(none)"
                    inferred = infer_prefix(samples)

                    joined_samples = "; ".join(str(x) for x in samples) if samples else ""
                    md_lines.append(
                        f"| `{table}` | `{column}` | `{dtype}` | {total} | {joined_samples} | {cls} | {inferred} |\n"
                    )

                    all_rows.append({
                        "database": db,
                        "table": table,
                        "column": column,
                        "data_type": dtype,
                        "non_empty_count": total,
                        "samples": "; ".join(str(x) for x in samples) if samples else "",
                        "classification": cls,
                        "inferred_prefix": inferred,
                    })
            finally:
                db_conn.close()

        # Write CSV
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "database", "table", "column", "data_type", "non_empty_count",
                    "samples", "classification", "inferred_prefix",
                ],
            )
            writer.writeheader()
            for row in all_rows:
                writer.writerow(row)

        # Summary heuristics
        url_like = sum(1 for r in all_rows if r["classification"] in {"url", "url_object_storage", "s3_uri"})
        key_like = sum(1 for r in all_rows if r["classification"] in {"object_key"})
        md_lines.append("\n---\n")
        md_lines.append(f"Summary: url-like columns={url_like}, object-key-like columns={key_like}, total={len(all_rows)}\n")
        md_lines.append("\nRecommendations:\n")
        md_lines.append("- Prefer storing object keys over full URLs; construct URLs at runtime via configured endpoint.\n")
        md_lines.append("- Migrate by mirroring prefixes discovered in `inferred_prefix` to TOS (map to miker/<env>/<service>/...).\n")

        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))

        print("[OK] Reports written:")
        print(md_path)
        print(csv_path)

    finally:
        root_conn.close()


if __name__ == "__main__":
    main()


