import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

BRAIN_DIR = Path.home() / ".vibeaudit"
BRAIN_DB = BRAIN_DIR / "brain.db"


def init_brain_db():
    BRAIN_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(BRAIN_DB))
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS audits (
        id INTEGER PRIMARY KEY,
        source TEXT,
        score INTEGER,
        security_score INTEGER,
        logic_score INTEGER,
        scale_score INTEGER,
        quality_score INTEGER,
        issue_count INTEGER,
        verdict TEXT,
        raw_output TEXT,
        saved_at TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS test_cases (
        id INTEGER PRIMARY KEY,
        text TEXT,
        created_at TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS criteria (
        id INTEGER PRIMARY KEY,
        text TEXT,
        created_at TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS patterns (
        id INTEGER PRIMARY KEY,
        name TEXT,
        pattern TEXT,
        category TEXT,
        severity TEXT,
        description TEXT,
        created_at TEXT
    )''')

    conn.commit()
    conn.close()


def save_audit_to_brain(source: str, result, raw_output: str):
    conn = sqlite3.connect(str(BRAIN_DB))
    c = conn.cursor()
    c.execute('''INSERT INTO audits
        (source, score, security_score, logic_score, scale_score, quality_score, issue_count, verdict, raw_output, saved_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (source, result.overall_score, result.security_score, result.logic_score,
         result.scale_score, result.quality_score, len(result.issues),
         result.verdict, raw_output, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_audit_history(limit: int = 20) -> List[Dict]:
    conn = sqlite3.connect(str(BRAIN_DB))
    c = conn.cursor()
    c.execute('''SELECT source, score, security_score, logic_score, scale_score,
        quality_score, issue_count, verdict, saved_at FROM audits ORDER BY saved_at DESC LIMIT ?''',
        (limit,))
    rows = c.fetchall()
    conn.close()
    return [{
        "source": r[0], "score": r[1], "security": r[2], "logic": r[3],
        "scale": r[4], "quality": r[5], "issue_count": r[6],
        "verdict": r[7], "date": r[8][:10]
    } for r in rows]


def add_test_case(text: str):
    conn = sqlite3.connect(str(BRAIN_DB))
    c = conn.cursor()
    c.execute("INSERT INTO test_cases (text, created_at) VALUES (?, ?)",
              (text, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_test_cases() -> List[Dict]:
    conn = sqlite3.connect(str(BRAIN_DB))
    c = conn.cursor()
    c.execute("SELECT id, text, created_at FROM test_cases ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "text": r[1], "created_at": r[2]} for r in rows]


def delete_test_case(id: int):
    conn = sqlite3.connect(str(BRAIN_DB))
    c = conn.cursor()
    c.execute("DELETE FROM test_cases WHERE id = ?", (id,))
    conn.commit()
    conn.close()


def add_criteria(text: str):
    conn = sqlite3.connect(str(BRAIN_DB))
    c = conn.cursor()
    c.execute("INSERT INTO criteria (text, created_at) VALUES (?, ?)",
              (text, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_criteria() -> List[Dict]:
    conn = sqlite3.connect(str(BRAIN_DB))
    c = conn.cursor()
    c.execute("SELECT id, text, created_at FROM criteria ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "text": r[1], "created_at": r[2]} for r in rows]


def delete_criteria(id: int):
    conn = sqlite3.connect(str(BRAIN_DB))
    c = conn.cursor()
    c.execute("DELETE FROM criteria WHERE id = ?", (id,))
    conn.commit()
    conn.close()


def add_pattern(name: str, pattern: str, category: str, severity: str, description: str):
    conn = sqlite3.connect(str(BRAIN_DB))
    c = conn.cursor()
    c.execute('''INSERT INTO patterns (name, pattern, category, severity, description, created_at)
        VALUES (?, ?, ?, ?, ?, ?)''',
        (name, pattern, category, severity, description, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_patterns() -> List[Dict]:
    conn = sqlite3.connect(str(BRAIN_DB))
    c = conn.cursor()
    c.execute("SELECT id, name, pattern, category, severity, description FROM patterns")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "pattern": r[2], "category": r[3],
             "severity": r[4], "description": r[5]} for r in rows]


def export_to_obsidian(vault_path: str) -> str:
    if not vault_path:
        return "No vault path set"

    vault = Path(vault_path)
    if not vault.exists():
        return f"Vault not found: {vault_path}"

    brain_dir = vault / "VibeAudit"
    brain_dir.mkdir(exist_ok=True)

    conn = sqlite3.connect(str(BRAIN_DB))
    c = conn.cursor()

    c.execute("SELECT source, score, verdict, saved_at, raw_output FROM audits ORDER BY saved_at DESC LIMIT 50")
    audits = c.fetchall()
    conn.close()

    for audit in audits:
        source = audit[0].replace("/", "-").replace("\\", "-")[:50]
        date = audit[3][:10]
        filename = f"{date}_{source}.md"
        content = f"""---
date: {audit[3]}
score: {audit[1]}
---

# {audit[0]}

**Score:** {audit[1]}/100

## Verdict
{audit[2]}

## Raw Output
```
{audit[4]}
```
"""
        (brain_dir / filename).write_text(content, encoding="utf-8")

    return f"Exported {len(audits)} audits to {brain_dir}"


def import_from_obsidian(vault_path: str) -> str:
    if not vault_path:
        return "No vault path set"

    vault = Path(vault_path)
    vibeaudit_dir = vault / "VibeAudit"

    if not vibeaudit_dir.exists():
        return "No VibeAudit folder in vault"

    imported = 0
    for md_file in vibeaudit_dir.glob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        if "score:" in content.lower():
            imported += 1

    return f"Found {imported} audit files in vault"