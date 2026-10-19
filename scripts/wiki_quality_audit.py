#!/usr/bin/env python3
"""Maintain the single active WIKI quality/clarification issue ledger.

The ledger is a Markdown file with a fenced JSON payload.  This tool never
scans the WIKI and never edits source pages; all state backups and tombstones
live outside the WIKI under ~/.codex/tmp/wiki-quality-audit.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

DEFAULT_WIKI = Path(os.environ.get("WIKI_ROOT", str(Path.home() / "WIKI")))
STATE_ROOT = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "tmp/wiki-quality-audit"
LEDGER_NAME = "质量审计日志.md"
ALLOWED_CATEGORIES = {"clarification", "quality"}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def ledger_path(root: Path) -> Path:
    return root / LEDGER_NAME


def payload_text(payload: dict) -> str:
    groups = [("clarification", "待用户澄清事项"), ("quality", "WIKI库质量问题")]
    sections = []
    for category, label in groups:
        rows = [x for x in payload["issues"] if x.get("category") == category]
        if rows:
            lines = [f"## {label}", ""]
            for n, issue in enumerate(rows, 1):
                lines.extend([
                    f"### {n}. {issue['title']}",
                    f"- **问题**：{issue['problem']}",
                    f"- **需要确认**：{issue['decisionNeeded']}",
                    f"- **页面/证据**：{'; '.join(issue['pages'])}；{issue['evidence']}",
                    ""
                ])
            sections.append("\n".join(lines))
    body = "\n\n".join(sections)
    intro = "仅保留未解决问题。发现先记录，用户裁决后修正相关页面并读回，实际解决后移除；依据留同任务log.md与库外关闭记录。相同问题沿稳定ID合并，不凭旧报告复活。\n\n"
    return "---\ntitle: WIKI质量审计日志\ndescription: 事实澄清与知识库健康问题的唯一未解决台账\ncreated: \"2026-10-19\"\nupdated: \"" + now_iso() + "\"\ntype: quality-ledger\nstatus: active\naudience: internal\ntags: [wiki, quality, audit]\n---\n\n# WIKI质量审计日志\n\n" + intro + body + "\n\n<details>\n<summary>机器台账（唯一数据源）</summary>\n\n```json\n" + json.dumps(payload, ensure_ascii=False, indent=2) + "\n```\n\n</details>\n"


def parse_ledger(path: Path) -> tuple[dict, str]:
    if not path.exists():
        return {"version": 1, "issues": []}, ""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"读取台账失败，拒绝覆盖: {exc}")
    match = re.search(r"```json\s*\n(.*?)\n```", raw, re.S)
    if not match:
        raise RuntimeError("台账缺少 fenced JSON，拒绝覆盖")
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"台账 JSON 损坏，拒绝覆盖: {exc}")
    validate_payload(data)
    return data, raw


def validate_payload(data: dict) -> None:
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("issues"), list):
        raise RuntimeError("台账必须是 {version:1, issues:[...]}")
    seen = set()
    for issue in data["issues"]:
        validate_issue(issue)
        if issue["id"] in seen:
            raise RuntimeError(f"台账存在重复稳定ID: {issue['id']}")
        seen.add(issue["id"])


def validate_issue(issue: dict) -> None:
    required = ("id", "category", "title", "problem", "decisionNeeded", "pages", "evidence", "firstSeen", "updated")
    if not isinstance(issue, dict) or any(not issue.get(k) for k in required):
        raise RuntimeError("问题项缺少必填字段")
    if issue["category"] not in ALLOWED_CATEGORIES:
        raise RuntimeError(f"category必须为 clarification 或 quality: {issue.get('id')}")
    if not isinstance(issue["pages"], list) or not all(isinstance(p, str) and p for p in issue["pages"]):
        raise RuntimeError(f"pages格式错误: {issue.get('id')}")


def state_dir() -> Path:
    return STATE_ROOT


def state_paths() -> tuple[Path, Path, Path]:
    d = state_dir()
    return d / "lock", d / "state.json", d / "history.jsonl"


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"tombstones": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"外部状态损坏，拒绝写入: {exc}")
    if not isinstance(data, dict) or not isinstance(data.get("tombstones", {}), dict):
        raise RuntimeError("外部状态格式错误，拒绝写入")
    return data


class LedgerLock:
    def __init__(self, write: bool):
        self.write = write
        self.fd = None

    def __enter__(self):
        lock, _, _ = state_paths()
        if self.write:
            lock.parent.mkdir(parents=True, exist_ok=True)
        else:
            if not lock.exists():
                return self
        # Read-only inspection must never create a lock file or directory.
        self.fd = open(lock, "a+" if self.write else "r", encoding="utf-8")
        fcntl.flock(self.fd.fileno(), fcntl.LOCK_EX if self.write else fcntl.LOCK_SH)
        return self

    def __exit__(self, *_):
        if self.fd:
            fcntl.flock(self.fd.fileno(), fcntl.LOCK_UN)
            self.fd.close()


def atomic_write(path: Path, text: str, dry_run: bool) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def backup(path: Path, dry_run: bool) -> None:
    if dry_run or not path.exists():
        return
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = state_dir() / "backups" / f"{path.name}.{stamp}.{hashlib.sha256(path.read_bytes()).hexdigest()[:12]}.bak"
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, out)


def append_history(event: dict, dry_run: bool) -> None:
    if dry_run:
        return
    _, _, history = state_paths()
    history.parent.mkdir(parents=True, exist_ok=True)
    with history.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def write_state(data: dict, dry_run: bool) -> None:
    _, state, _ = state_paths()
    atomic_write(state, json.dumps(data, ensure_ascii=False, indent=2) + "\n", dry_run)


def load_input(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"输入 JSON 无法读取: {exc}")
    issues = data.get("issues") if isinstance(data, dict) and "issues" in data else [data]
    if not isinstance(issues, list):
        raise RuntimeError("输入必须是单项对象或 issues 数组")
    for issue in issues:
        validate_issue(issue)
    return issues


def upsert_data(data: dict, input_issues: list[dict], state: dict) -> tuple[dict, list[str], list[str]]:
    by_id = {i["id"]: i for i in data["issues"]}
    changed, skipped = [], []
    for incoming in input_issues:
        if incoming["id"] in state["tombstones"]:
            skipped.append(incoming["id"])
            continue
        old = by_id.get(incoming["id"])
        expected = incoming.get("expectedUpdated")
        if old and expected is not None and old["updated"] != expected:
            raise RuntimeError(f"并发保护失败: id={incoming['id']} expectedUpdated={expected}, actual={old['updated']}")
        merged = dict(old or {})
        merged.update(incoming)
        merged.pop("expectedUpdated", None)
        if old and old.get("firstSeen"):
            merged["firstSeen"] = old["firstSeen"]
        merged["updated"] = now_iso()
        by_id[incoming["id"]] = merged
        changed.append(incoming["id"])
    data["issues"] = list(by_id.values())
    validate_payload(data)
    return data, changed, skipped


def cmd_list(args) -> int:
    with LedgerLock(False):
        data, _ = parse_ledger(ledger_path(Path(args.wiki_root)))
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def cmd_upsert(args) -> int:
    root = Path(args.wiki_root)
    input_issues = load_input(Path(args.file))
    path = ledger_path(root)
    with LedgerLock(not args.dry_run):
        data, _ = parse_ledger(path)
        _, state_path, _ = state_paths()
        state = load_state(state_path)
        data, changed, skipped = upsert_data(data, input_issues, state)
        if changed:
            backup(path, args.dry_run)
            atomic_write(path, payload_text(data), args.dry_run)
        print(json.dumps({"changed": changed, "skipped_tombstones": skipped, "dry_run": args.dry_run}, ensure_ascii=False))
    return 0


def cmd_resolve(args) -> int:
    if not args.decision.strip() or not args.evidence.strip() or not args.expected_updated.strip():
        raise RuntimeError("resolve必须提供非空 decision、evidence、expected_updated")
    path = ledger_path(Path(args.wiki_root))
    with LedgerLock(not args.dry_run):
        data, _ = parse_ledger(path)
        state = load_state(state_paths()[1])
        matches = [i for i in data["issues"] if i["id"] == args.id]
        if not matches:
            raise RuntimeError("稳定ID不存在或已解决")
        issue = matches[0]
        if issue["updated"] != args.expected_updated:
            raise RuntimeError(f"并发保护失败: expected_updated={args.expected_updated}, actual={issue['updated']}")
        data["issues"] = [i for i in data["issues"] if i["id"] != args.id]
        state["tombstones"][args.id] = {"resolvedAt": now_iso(), "decision": args.decision, "evidence": args.evidence}
        validate_payload(data)
        # Commit the tombstone first. If the ledger write fails afterwards,
        # the active item remains visible but cannot be resurrected by sync.
        write_state(state, args.dry_run)
        backup(path, args.dry_run)
        atomic_write(path, payload_text(data), args.dry_run)
        append_history({"event": "resolve", "id": args.id, "decision": args.decision, "evidence": args.evidence, "at": now_iso()}, args.dry_run)
        print(json.dumps({"resolved": args.id, "dry_run": args.dry_run}, ensure_ascii=False))
    return 0


def cmd_sync_metrics(args) -> int:
    try:
        metrics = json.loads(Path(args.file).read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"metrics JSON无法读取: {exc}")
    nested = metrics.get("metrics", {}) if isinstance(metrics, dict) else {}
    if not isinstance(nested, dict):
        nested = {}
    items = []
    metric_date = metrics.get("date") or metrics.get("generated_at") or now_iso()
    existing, _ = parse_ledger(ledger_path(Path(args.wiki_root)))
    existing_by_id = {i["id"]: i for i in existing["issues"]}
    for key, title in (("dead_links", "WIKI死链指标"), ("orphan_pages", "WIKI孤儿页指标")):
        value = nested.get(key, metrics.get(key))
        if isinstance(value, dict):
            count = value.get("count", value.get("value"))
            evidence = value.get("evidence", f"metrics:{key}")
        else:
            count, evidence = value, f"metrics:{key}"
        if isinstance(count, (int, float)) and count > 0:
            old = existing_by_id.get(f"wiki-{key}")
            if old:
                item = dict(old)
                item.update({"metricCount": count, "metricDate": metric_date, "evidence": evidence})
            else:
                item = {"id": f"wiki-{key}", "category": "quality", "title": title, "problem": f"当前指标为{count}，需核对范围与修复计划。", "decisionNeeded": "确认修复范围与验收证据。", "pages": ["system/memory/ops/"], "evidence": evidence, "firstSeen": metric_date, "updated": metric_date, "metricCount": count, "metricDate": metric_date}
            items.append(item)
    with LedgerLock(not args.dry_run):
        data, _ = parse_ledger(ledger_path(Path(args.wiki_root)))
        state = load_state(state_paths()[1])
        if not items:
            print(json.dumps({"changed": [], "dry_run": args.dry_run}, ensure_ascii=False))
            return 0
        data, changed, skipped = upsert_data(data, items, state)
        backup(ledger_path(Path(args.wiki_root)), args.dry_run)
        atomic_write(ledger_path(Path(args.wiki_root)), payload_text(data), args.dry_run)
        print(json.dumps({"changed": changed, "skipped_tombstones": skipped, "dry_run": args.dry_run}, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wiki-root", default=str(DEFAULT_WIKI))
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("list"); p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_list)
    p = sub.add_parser("upsert"); p.add_argument("--file", required=True); p.add_argument("--dry-run", action="store_true"); p.set_defaults(func=cmd_upsert)
    p = sub.add_parser("resolve"); p.add_argument("--id", required=True); p.add_argument("--decision", required=True); p.add_argument("--evidence", required=True); p.add_argument("--expected-updated", required=True); p.add_argument("--dry-run", action="store_true"); p.set_defaults(func=cmd_resolve)
    p = sub.add_parser("sync-metrics"); p.add_argument("--file", required=True); p.add_argument("--dry-run", action="store_true"); p.set_defaults(func=cmd_sync_metrics)
    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
