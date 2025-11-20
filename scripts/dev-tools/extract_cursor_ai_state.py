#!/usr/bin/env python3
"""
从 Cursor 的 state.vscdb 中提取 aiService 相关键值，尝试恢复提示历史并导出为 Markdown。
"""

import os
import sqlite3
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# 根据当前用户环境和 workspaceStorage ID 定位到 state.vscdb
DB_PATH = os.path.expanduser(
    "/Users/jasonhong/Library/Application Support/Cursor/User/workspaceStorage/708507d353112795aedc69ff6f130fdf/state.vscdb"
)

# 导出目录：使用当前仓库下的 .specstory/history
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_DIR = os.path.join(REPO_ROOT, ".specstory", "history")


def ensure_history_dir() -> None:
    os.makedirs(HISTORY_DIR, exist_ok=True)


def connect_db(path: str) -> sqlite3.Connection:
    if not os.path.exists(path):
        raise FileNotFoundError(f"state.vscdb not found at: {path}")
    # 以只读方式打开，避免对 Cursor 产生任何影响
    uri = f"file:{path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    return conn


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (name,)
    )
    return cur.fetchone() is not None


def fetch_ai_related_rows(conn: sqlite3.Connection) -> List[Tuple[str, str]]:
    """
    从 cursorDiskKV / ItemTable 中挑选出和 AI / 聊天相关的键值。
    """
    rows: List[Tuple[str, str]] = []

    # keys 里通常包含这些前缀/片段
    like_patterns = [
        "%aiService%",
        "%aichat%",
        "%composerChat%",
        "%workbench.panel.aichat%",
        "%workbench.panel.composerChatViewPanel%",
    ]

    where_clause = " OR ".join(["key LIKE ?"] * len(like_patterns))

    # 1) 先查 cursorDiskKV（如果存在）
    if table_exists(conn, "cursorDiskKV"):
        try:
            sql = f"SELECT key, value FROM cursorDiskKV WHERE {where_clause};"
            cur = conn.execute(sql, like_patterns)
            for key, value in cur.fetchall():
                if value is None:
                    continue
                if isinstance(value, bytes):
                    try:
                        text = value.decode("utf-8", errors="ignore")
                    except Exception:
                        continue
                else:
                    text = str(value)
                rows.append((key, text))
        except Exception:
            pass

    # 2) 再查 ItemTable（如果结构中有 key/value 列）
    if table_exists(conn, "ItemTable"):
        try:
            cur = conn.execute("PRAGMA table_info(ItemTable);")
            cols = [r[1] for r in cur.fetchall()]
            if "key" in cols and "value" in cols:
                sql = f"SELECT key, value FROM ItemTable WHERE {where_clause};"
                cur = conn.execute(sql, like_patterns)
                for key, value in cur.fetchall():
                    if value is None:
                        continue
                    if isinstance(value, bytes):
                        try:
                            text = value.decode("utf-8", errors="ignore")
                        except Exception:
                            continue
                    else:
                        text = str(value)
                    rows.append((key, text))
        except Exception:
            pass

    return rows


def parse_json_safe(text: str) -> Optional[Any]:
    text = text.strip()
    if not text:
        return None
    # 有些值可能是前面有前缀的 JSON，这里简单尝试从第一个 { 或 [ 开始解析
    first_brace = min(
        [i for i in [text.find("{"), text.find("[")] if i != -1] or [-1]
    )
    candidate = text[first_brace:] if first_brace > 0 else text
    try:
        return json.loads(candidate)
    except Exception:
        return None


def looks_like_prompt(s: str) -> bool:
    """
    粗略判断一个字符串是否像是用户输入的提示 / 问题，而不是路径、配置等。
    """
    s = s.strip()
    if len(s) < 4:
        return False
    # 过滤明显的路径或文件名
    if any(ch in s for ch in ["/", "\\", ".yaml", ".json", ".ts", ".tsx"]):
        # 如果包含中文或问号，仍然认为可能是问题
        if not any("\u4e00" <= c <= "\u9fff" for c in s) and "?" not in s and "？" not in s:
            return False
    # 含中文、英文问句、命令式等都算
    if any("\u4e00" <= c <= "\u9fff" for c in s):
        return True
    if "?" in s or "？" in s:
        return True
    # 较长的英文文本也保留
    if len(s) >= 20:
        return True
    return False


def extract_timestamp(d: Dict[str, Any]) -> Optional[float]:
    """
    从一个 dict 中尽量抽取时间戳，支持多种常见字段名。
    返回秒级 Unix 时间戳（float），若失败则返回 None。
    """
    candidate_keys = [
        "timestamp",
        "createdAt",
        "updatedAt",
        "time",
        "date",
        "ts",
    ]
    for k in candidate_keys:
        if k in d:
            v = d[k]
            # 数字直接认为是时间戳（毫秒或秒）
            if isinstance(v, (int, float)):
                # 粗略判断毫秒 / 秒
                if v > 1e12:
                    return v / 1000.0
                return float(v)
            # 字符串尝试解析
            if isinstance(v, str):
                v = v.strip()
                if not v:
                    continue
                # 先尝试数字
                try:
                    num = float(v)
                    if num > 1e12:
                        return num / 1000.0
                    return num
                except Exception:
                    pass
                # 再尝试 ISO8601
                try:
                    dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
                    return dt.replace(tzinfo=timezone.utc).timestamp()
                except Exception:
                    pass
    return None


def walk_json_and_collect(
    node: Any,
    current_ts: Optional[float],
    collected: List[Dict[str, Any]],
) -> None:
    """
    深度遍历 JSON，收集看起来像提示/问题的字符串和相关时间戳。
    """
    if isinstance(node, dict):
        # 先从当前层尝试更新时间戳
        ts_here = extract_timestamp(node) or current_ts

        # 常见字段名优先作为候选
        hint_fields = [
            "prompt",
            "input",
            "text",
            "content",
            "message",
            "question",
            "command",
        ]
        for key, val in node.items():
            if isinstance(val, str):
                if key in hint_fields or looks_like_prompt(val):
                    collected.append(
                        {
                            "text": val.strip(),
                            "timestamp": ts_here,
                        }
                    )
            else:
                walk_json_and_collect(val, ts_here, collected)

    elif isinstance(node, list):
        for item in node:
            walk_json_and_collect(item, current_ts, collected)
    else:
        # 其他类型忽略
        return


def recover_prompts_from_rows(
    rows: List[Tuple[str, str]]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    针对每个 key 的 JSON value，提取出可能的提示 / 聊天内容。
    返回结构：{ key: [ {text, timestamp}, ... ] }
    """
    result: Dict[str, List[Dict[str, Any]]] = {}
    for key, text in rows:
        data = parse_json_safe(text)
        if data is None:
            continue
        collected: List[Dict[str, Any]] = []
        walk_json_and_collect(data, None, collected)
        if collected:
            # 按时间排序（无时间戳的排在最后）
            collected_sorted = sorted(
                collected,
                key=lambda x: x["timestamp"] if x.get("timestamp") is not None else 1e20,
            )
            result[key] = collected_sorted
    return result


def ts_to_str(ts: Optional[float]) -> str:
    if ts is None:
        return ""
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def build_markdown(
    recovered: Dict[str, List[Dict[str, Any]]],
    debug: Optional[Dict[str, Any]] = None,
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")
    lines: List[str] = []
    lines.append("<!-- Generated by extract_cursor_ai_state.py -->")
    lines.append("")
    lines.append(f"<!-- Cursor state.vscdb AI prompt recovery at {now} -->")
    lines.append("")
    lines.append(f"**Source DB**: `{DB_PATH}`")
    lines.append("")

    if not recovered:
        lines.append("未从 state.vscdb 中解析到任何看起来像聊天提示/问题的内容。")
        if debug:
            tables = debug.get("tables") or []
            lines.append("")
            lines.append("### 调试信息")
            lines.append("")
            lines.append("**现有数据表**:")
            if tables:
                for t in tables:
                    lines.append(f"- `{t}`")
            else:
                lines.append("- （未能读取到表信息）")

            columns = debug.get("cursorDiskKV_columns") or []
            lines.append("")
            lines.append("**cursorDiskKV 表结构（PRAGMA table_info）**:")
            if columns:
                for col in columns:
                    lines.append(
                        f"- cid={col.get('cid')} name=`{col.get('name')}` type={col.get('type')}"
                    )
            else:
                lines.append("- （未能读取到 cursorDiskKV 列信息）")

            item_columns = debug.get("ItemTable_columns") or []
            lines.append("")
            lines.append("**ItemTable 表结构（PRAGMA table_info）**:")
            if item_columns:
                for col in item_columns:
                    lines.append(
                        f"- cid={col.get('cid')} name=`{col.get('name')}` type={col.get('type')}"
                    )
            else:
                lines.append("- （未能读取到 ItemTable 列信息）")

            sample_keys = debug.get("cursorDiskKV_keys") or []
            lines.append("")
            lines.append("**cursorDiskKV 表中部分 key 示例（最多 100 条）**:")
            if sample_keys:
                for k in sample_keys:
                    lines.append(f"- `{k}`")
            else:
                lines.append("- （未能读取到 cursorDiskKV.key 示例，可能不存在该表或结构不同）")
        return "\n".join(lines)

    for idx, (key, prompts) in enumerate(sorted(recovered.items()), start=1):
        lines.append("")
        lines.append(f"## 会话组 {idx}: `{key}`")
        lines.append("")
        for i, item in enumerate(prompts, start=1):
            ts = item.get("timestamp")
            ts_str = ts_to_str(ts)
            header = f"- **消息 {i}**"
            if ts_str:
                header += f" · {ts_str}"
            lines.append(header)
            lines.append("")
            lines.append("```text")
            lines.append(item.get("text", ""))
            lines.append("```")
            lines.append("")

    return "\n".join(lines)


def main() -> None:
    ensure_history_dir()

    debug_info: Dict[str, Any] = {}

    try:
        conn = connect_db(DB_PATH)
    except Exception as e:
        ensure_history_dir()
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%MZ")
        error_path = os.path.join(
            HISTORY_DIR, f"{ts}-cursor-ai-prompts-recovery-error.md"
        )
        with open(error_path, "w", encoding="utf-8") as f:
            f.write("无法连接到 state.vscdb：\n\n")
            f.write(str(e))
        return

    try:
        # 收集调试信息：表列表与 cursorDiskKV 的部分 key
        try:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
            )
            debug_info["tables"] = [r[0] for r in cur.fetchall()]
        except Exception:
            debug_info["tables"] = []

        try:
            if table_exists(conn, "cursorDiskKV"):
                # 记录 cursorDiskKV 的列结构
                try:
                    cur = conn.execute("PRAGMA table_info(cursorDiskKV);")
                    debug_info["cursorDiskKV_columns"] = [
                        {"cid": r[0], "name": r[1], "type": r[2]}
                        for r in cur.fetchall()
                    ]
                except Exception:
                    debug_info["cursorDiskKV_columns"] = []

                cur = conn.execute(
                    "SELECT key FROM cursorDiskKV LIMIT 100;"
                )
                debug_info["cursorDiskKV_keys"] = [r[0] for r in cur.fetchall()]
            else:
                debug_info["cursorDiskKV_keys"] = []
        except Exception:
            debug_info["cursorDiskKV_keys"] = []

        # ItemTable 结构信息
        try:
            if table_exists(conn, "ItemTable"):
                try:
                    cur = conn.execute("PRAGMA table_info(ItemTable);")
                    debug_info["ItemTable_columns"] = [
                        {"cid": r[0], "name": r[1], "type": r[2]}
                        for r in cur.fetchall()
                    ]
                except Exception:
                    debug_info["ItemTable_columns"] = []
            else:
                debug_info["ItemTable_columns"] = []
        except Exception:
            debug_info["ItemTable_columns"] = []

        rows = fetch_ai_related_rows(conn)
    finally:
        conn.close()

    recovered = recover_prompts_from_rows(rows)

    # 同时把原始 JSON value 也按 key 导出一份，方便后续更精细分析 / 恢复
    try:
        for key, text in rows:
            safe_key = (
                key.replace("/", "_")
                .replace("\\", "_")
                .replace(":", "_")
                .replace(" ", "_")
            )
            raw_path = os.path.join(HISTORY_DIR, f"raw-{safe_key}.json")
            # 避免覆盖已有手动分析结果，只在文件不存在时写入
            if not os.path.exists(raw_path):
                with open(raw_path, "w", encoding="utf-8") as f:
                    f.write(text)
    except Exception:
        # 原始导出失败不影响主流程
        pass

    md_content = build_markdown(recovered, debug=debug_info)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%MZ")
    out_path = os.path.join(
        HISTORY_DIR, f"{ts}-cursor-ai-prompts-recovered.md"
    )
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md_content)


if __name__ == "__main__":
    main()


