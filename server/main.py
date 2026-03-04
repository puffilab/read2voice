import asyncio
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.requests import Request

from server.epub_parser import Chapter, chapter_preview, parse_document_bytes, split_text_for_tts
from server.tts_engines import EngineType, list_engine_voices, output_content_type, synthesize_text

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("APP_DATA_DIR", str(BASE_DIR.parent / "data"))).resolve()
DOCS_DIR = DATA_DIR / "docs"
JOBS_DIR = DATA_DIR / "jobs"
AUDIO_DIR = DATA_DIR / "audio"
USERS_FILE = DATA_DIR / "users.json"
AUTH_SECRET_FILE = DATA_DIR / "auth_secret.txt"
DB_FILE = DATA_DIR / "app.sqlite3"

MAX_STORED_JOBS = int(os.getenv("MAX_STORED_JOBS", "50"))
TOKEN_TTL_SECONDS = int(os.getenv("TOKEN_TTL_SECONDS", str(7 * 24 * 3600)))
ENABLE_SIGNUP = os.getenv("ENABLE_SIGNUP", "1") == "1"
ENABLE_MEMBERSHIP = os.getenv("ENABLE_MEMBERSHIP", "0") == "1"
DEFAULT_LOCAL_USER = os.getenv("DEFAULT_LOCAL_USER", "local_user")

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,32}$")
INVALID_FILENAME_CHARS_RE = re.compile(r'[\\/:*?"<>|]+')
FILENAME_SPACES_RE = re.compile(r"\s+")

ALLOWED_ENGINES = {"openai", "edge_tts", "custom_http"}
ALLOWED_CONFIG_KEYS = {
    "api_key",
    "endpoint",
    "model",
    "voice",
    "instructions",
    "custom_headers_json",
    "speed",
    "output_format",
}


@dataclass
class UserRecord:
    username: str
    password_hash: str
    password_salt: str
    created_at: datetime
    tier: str = "free"
    is_admin: bool = False
    tts_config: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class StoredDocument:
    id: str
    owner: str
    filename: str
    created_at: datetime
    chapters: list[Chapter]


@dataclass
class SynthesisJob:
    id: str
    owner: str
    status: str
    created_at: datetime
    updated_at: datetime
    engine: str
    output_format: str
    total_chunks: int
    completed_chunks: int
    progress: float
    error: str | None
    audio_path: str | None
    content_type: str | None
    filename: str | None
    source_type: str | None
    source_doc_id: str | None
    source_chapter_index: int | None
    source_chapter_title: str | None
    source_book_title: str | None


users: dict[str, UserRecord] = {}
documents: dict[str, StoredDocument] = {}
jobs: dict[str, SynthesisJob] = {}
auth_secret: bytes = b""
synthesis_semaphore = asyncio.Semaphore(1)
db_conn: sqlite3.Connection | None = None
db_lock = threading.Lock()

app = FastAPI(title="EPUB TTS Server", version="2.0.0")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


class AuthRequest(BaseModel):
    username: str
    password: str


class ProfileConfigRequest(BaseModel):
    configs: dict[str, dict[str, Any]] = Field(default_factory=dict)


class PlanUpdateRequest(BaseModel):
    display_name: str | None = None
    max_uploads_month: int
    max_syntheses_month: int


class UserTierUpdateRequest(BaseModel):
    tier: str


class SynthesizeRequest(BaseModel):
    engine: EngineType = Field(default="openai")
    doc_id: str | None = None
    chapter_index: int | None = None
    custom_text: str | None = None

    api_key: str | None = None
    endpoint: str | None = None
    model: str | None = None
    voice: str | None = None
    instructions: str | None = None
    custom_headers_json: str | None = None

    speed: float = 1.0
    output_format: str = "mp3"
    force_resynthesize: bool = False


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _dt_to_str(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _str_to_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _sanitize_filename_part(raw: str | None, fallback: str, max_len: int = 72) -> str:
    text = (raw or "").strip()
    if not text:
        text = fallback
    text = INVALID_FILENAME_CHARS_RE.sub(" ", text)
    text = FILENAME_SPACES_RE.sub(" ", text).strip(" .-_")
    if not text:
        text = fallback
    if len(text) > max_len:
        text = text[:max_len].rstrip(" .-_")
    return text or fallback


def _build_filename_from_source(source_meta: dict[str, Any], output_format: str, fallback_prefix: str) -> str:
    ext = (output_format or "mp3").lower()
    if source_meta.get("source_type") == "chapter":
        chapter_index = source_meta.get("source_chapter_index")
        book = _sanitize_filename_part(str(source_meta.get("source_book_title") or ""), "book")
        chapter_raw = source_meta.get("source_chapter_title")
        if not chapter_raw and chapter_index is not None:
            chapter_raw = f"chapter-{int(chapter_index) + 1}"
        chapter = _sanitize_filename_part(str(chapter_raw or ""), "chapter")
        return f"{book}-{chapter}.{ext}"
    return f"{fallback_prefix}.{ext}"


def _content_disposition_value(filename: str, attachment: bool) -> str:
    safe = _sanitize_filename_part(filename, "audio")
    ascii_fallback = safe.encode("ascii", "ignore").decode("ascii")
    ascii_fallback = _sanitize_filename_part(ascii_fallback, "audio")
    encoded = quote(safe, safe="")
    mode = "attachment" if attachment else "inline"
    return f'{mode}; filename="{ascii_fallback}"; filename*=UTF-8\'\'{encoded}'


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(raw: str) -> bytes:
    pad_len = (-len(raw)) % 4
    return base64.urlsafe_b64decode(raw + ("=" * pad_len))


def _json_write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)


def _json_read(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_FILE), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def _db_exec(sql: str, params: tuple[Any, ...] = ()) -> None:
    if db_conn is None:
        raise RuntimeError("Database is not initialized")
    with db_lock:
        db_conn.execute(sql, params)
        db_conn.commit()


def _db_fetchall(sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    if db_conn is None:
        raise RuntimeError("Database is not initialized")
    with db_lock:
        cur = db_conn.execute(sql, params)
        return cur.fetchall()


def _db_fetchone(sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
    if db_conn is None:
        raise RuntimeError("Database is not initialized")
    with db_lock:
        cur = db_conn.execute(sql, params)
        return cur.fetchone()


def _db_count(table: str) -> int:
    row = _db_fetchone(f"SELECT COUNT(*) AS c FROM {table}")
    return int(row["c"]) if row else 0


def _ensure_table_column(table: str, column: str, ddl: str) -> None:
    rows = _db_fetchall(f"PRAGMA table_info({table})")
    existing = {str(r["name"]) for r in rows}
    if column in existing:
        return
    _db_exec(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def _init_db() -> None:
    _db_exec(
        """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            created_at TEXT NOT NULL,
            tts_config_json TEXT NOT NULL
        )
        """
    )
    _ensure_table_column("users", "tier", "tier TEXT NOT NULL DEFAULT 'free'")
    _ensure_table_column("users", "is_admin", "is_admin INTEGER NOT NULL DEFAULT 0")
    _db_exec(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            owner TEXT NOT NULL,
            filename TEXT NOT NULL,
            created_at TEXT NOT NULL,
            chapters_json TEXT NOT NULL
        )
        """
    )
    _db_exec(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            owner TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            engine TEXT NOT NULL,
            output_format TEXT NOT NULL,
            total_chunks INTEGER NOT NULL,
            completed_chunks INTEGER NOT NULL,
            progress REAL NOT NULL,
            error TEXT NULL,
            audio_path TEXT NULL,
            content_type TEXT NULL,
            filename TEXT NULL,
            source_type TEXT NULL,
            source_doc_id TEXT NULL,
            source_chapter_index INTEGER NULL,
            source_chapter_title TEXT NULL,
            source_book_title TEXT NULL
        )
        """
    )
    _ensure_table_column("jobs", "source_book_title", "source_book_title TEXT NULL")
    _db_exec(
        """
        CREATE TABLE IF NOT EXISTS membership_plans (
            tier TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            max_uploads_month INTEGER NOT NULL,
            max_syntheses_month INTEGER NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    _db_exec(
        """
        CREATE TABLE IF NOT EXISTS usage_monthly (
            username TEXT NOT NULL,
            ym TEXT NOT NULL,
            upload_count INTEGER NOT NULL DEFAULT 0,
            synth_count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (username, ym)
        )
        """
    )
    _db_exec("CREATE INDEX IF NOT EXISTS idx_documents_owner ON documents(owner)")
    _db_exec("CREATE INDEX IF NOT EXISTS idx_jobs_owner_updated ON jobs(owner, updated_at DESC)")
    _db_exec("CREATE INDEX IF NOT EXISTS idx_usage_monthly_ym ON usage_monthly(ym)")


def _seed_default_plans() -> None:
    defaults = [
        ("free", "Free", 8, 60, 10),
        ("pro", "Pro", 60, 500, 20),
        ("vip", "VIP", -1, -1, 30),
    ]
    for tier, name, up_limit, syn_limit, order in defaults:
        _db_exec(
            """
            INSERT OR IGNORE INTO membership_plans (tier, display_name, max_uploads_month, max_syntheses_month, sort_order)
            VALUES (?, ?, ?, ?, ?)
            """,
            (tier, name, up_limit, syn_limit, order),
        )


def _ensure_admin_exists() -> None:
    admin_row = _db_fetchone("SELECT username FROM users WHERE is_admin = 1 LIMIT 1")
    if admin_row:
        return
    first_user = _db_fetchone("SELECT username FROM users ORDER BY created_at ASC LIMIT 1")
    if not first_user:
        return
    _db_exec("UPDATE users SET is_admin = 1 WHERE username = ?", (str(first_user["username"]),))


def _current_month_key() -> str:
    return _utc_now().strftime("%Y-%m")


def _get_plan_by_tier(tier: str) -> dict[str, Any]:
    row = _db_fetchone(
        "SELECT tier, display_name, max_uploads_month, max_syntheses_month, sort_order FROM membership_plans WHERE tier = ?",
        (tier,),
    )
    if not row:
        row = _db_fetchone(
            "SELECT tier, display_name, max_uploads_month, max_syntheses_month, sort_order FROM membership_plans WHERE tier = 'free'"
        )
    if not row:
        raise HTTPException(status_code=500, detail="Membership plan data is missing")
    return {
        "tier": str(row["tier"]),
        "display_name": str(row["display_name"]),
        "max_uploads_month": int(row["max_uploads_month"]),
        "max_syntheses_month": int(row["max_syntheses_month"]),
        "sort_order": int(row["sort_order"]),
    }


def _get_monthly_usage(username: str, ym: str | None = None) -> dict[str, int]:
    month = ym or _current_month_key()
    row = _db_fetchone(
        "SELECT upload_count, synth_count FROM usage_monthly WHERE username = ? AND ym = ?",
        (username, month),
    )
    if not row:
        return {"upload_count": 0, "synth_count": 0}
    return {"upload_count": int(row["upload_count"] or 0), "synth_count": int(row["synth_count"] or 0)}


def _consume_quota(username: str, action: str) -> dict[str, Any]:
    if not ENABLE_MEMBERSHIP or username == DEFAULT_LOCAL_USER:
        return {"allowed": True, "used": 0, "limit": -1, "remaining": -1, "action": action}

    user = _get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    plan = _get_plan_by_tier(user.tier)
    ym = _current_month_key()
    if action == "upload":
        limit_field = "max_uploads_month"
        usage_field = "upload_count"
        label = "upload"
    elif action == "synthesize":
        limit_field = "max_syntheses_month"
        usage_field = "synth_count"
        label = "synthesis"
    else:
        raise ValueError(f"Unsupported quota action: {action}")

    limit = int(plan[limit_field])
    if limit < 0:
        return {"allowed": True, "used": 0, "limit": -1, "remaining": -1, "action": label}

    if db_conn is None:
        raise RuntimeError("Database is not initialized")
    with db_lock:
        row = db_conn.execute(
            "SELECT upload_count, synth_count FROM usage_monthly WHERE username = ? AND ym = ?",
            (username, ym),
        ).fetchone()
        used = int(row[usage_field]) if row else 0
        if used >= limit:
            raise HTTPException(
                status_code=403,
                detail=f"Monthly {label} quota reached ({used}/{limit}) for tier '{plan['tier']}'",
            )
        if row:
            if usage_field == "upload_count":
                db_conn.execute(
                    "UPDATE usage_monthly SET upload_count = upload_count + 1 WHERE username = ? AND ym = ?",
                    (username, ym),
                )
            else:
                db_conn.execute(
                    "UPDATE usage_monthly SET synth_count = synth_count + 1 WHERE username = ? AND ym = ?",
                    (username, ym),
                )
        else:
            up = 1 if usage_field == "upload_count" else 0
            sy = 1 if usage_field == "synth_count" else 0
            db_conn.execute(
                "INSERT INTO usage_monthly (username, ym, upload_count, synth_count) VALUES (?, ?, ?, ?)",
                (username, ym, up, sy),
            )
        db_conn.commit()
        next_used = used + 1
    return {"allowed": True, "used": next_used, "limit": limit, "remaining": max(limit - next_used, 0), "action": label}


def _quota_payload_for_user(user: UserRecord) -> dict[str, Any]:
    if not ENABLE_MEMBERSHIP or user.username == DEFAULT_LOCAL_USER:
        return {
            "tier": "local",
            "tier_display_name": "Local",
            "month": _current_month_key(),
            "limits": {"uploads_month": -1, "syntheses_month": -1},
            "usage": {"uploads_month": 0, "syntheses_month": 0},
            "remaining": {"uploads_month": -1, "syntheses_month": -1},
        }

    plan = _get_plan_by_tier(user.tier)
    usage = _get_monthly_usage(user.username)
    max_uploads = int(plan["max_uploads_month"])
    max_syn = int(plan["max_syntheses_month"])
    return {
        "tier": plan["tier"],
        "tier_display_name": plan["display_name"],
        "month": _current_month_key(),
        "limits": {
            "uploads_month": max_uploads,
            "syntheses_month": max_syn,
        },
        "usage": {
            "uploads_month": usage["upload_count"],
            "syntheses_month": usage["synth_count"],
        },
        "remaining": {
            "uploads_month": (-1 if max_uploads < 0 else max(max_uploads - usage["upload_count"], 0)),
            "syntheses_month": (-1 if max_syn < 0 else max(max_syn - usage["synth_count"], 0)),
        },
    }


def _normalize_limit(value: int) -> int:
    v = int(value)
    if v < -1:
        raise HTTPException(status_code=400, detail="Quota limit must be -1(unlimited) or >= 0")
    return v


def _membership_feature_required() -> None:
    if not ENABLE_MEMBERSHIP:
        raise HTTPException(status_code=404, detail="Membership feature is disabled")


def _ensure_default_local_user() -> None:
    if _get_user_by_username(DEFAULT_LOCAL_USER) is not None:
        return
    salt_hex = secrets.token_hex(16)
    user = UserRecord(
        username=DEFAULT_LOCAL_USER,
        password_hash=_hash_password("local-mode", salt_hex),
        password_salt=salt_hex,
        created_at=_utc_now(),
        tier="free",
        is_admin=False,
        tts_config={},
    )
    users[user.username] = user
    _save_user(user)


def _migrate_legacy_json_data_if_needed() -> None:
    if _db_count("users") == 0 and USERS_FILE.exists():
        raw = _json_read(USERS_FILE, [])
        if isinstance(raw, list):
            for item in raw:
                try:
                    username = str(item["username"]).strip()
                    if not username:
                        continue
                    tts_config = _sanitize_profile_configs(item.get("tts_config") or {})
                    _db_exec(
                        """
                        INSERT OR REPLACE INTO users (
                            username, password_hash, password_salt, created_at, tts_config_json, tier, is_admin
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            username,
                            str(item["password_hash"]),
                            str(item["password_salt"]),
                            _dt_to_str(_str_to_dt(str(item["created_at"]))),
                            json.dumps(tts_config, ensure_ascii=False),
                            str(item.get("tier") or "free"),
                            (1 if bool(item.get("is_admin")) else 0),
                        ),
                    )
                except Exception:
                    continue

    if _db_count("documents") == 0 and DOCS_DIR.exists():
        for path in DOCS_DIR.glob("*.json"):
            raw = _json_read(path, {})
            if not isinstance(raw, dict):
                continue
            try:
                chapters = [
                    {"title": str(c["title"]), "text": str(c["text"])}
                    for c in raw.get("chapters", [])
                    if isinstance(c, dict)
                ]
                _db_exec(
                    """
                    INSERT OR REPLACE INTO documents (id, owner, filename, created_at, chapters_json)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(raw["id"]),
                        str(raw["owner"]),
                        str(raw["filename"]),
                        _dt_to_str(_str_to_dt(str(raw["created_at"]))),
                        json.dumps(chapters, ensure_ascii=False),
                    ),
                )
            except Exception:
                continue

    if _db_count("jobs") == 0 and JOBS_DIR.exists():
        for path in JOBS_DIR.glob("*.json"):
            raw = _json_read(path, {})
            if not isinstance(raw, dict):
                continue
            try:
                _db_exec(
                    """
                    INSERT OR REPLACE INTO jobs (
                        id, owner, status, created_at, updated_at, engine, output_format,
                        total_chunks, completed_chunks, progress, error, audio_path, content_type, filename,
                        source_type, source_doc_id, source_chapter_index, source_chapter_title, source_book_title
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(raw["id"]),
                        str(raw["owner"]),
                        str(raw.get("status", "failed")),
                        _dt_to_str(_str_to_dt(str(raw["created_at"]))),
                        _dt_to_str(_str_to_dt(str(raw.get("updated_at", raw["created_at"])))),
                        str(raw["engine"]),
                        str(raw.get("output_format", "mp3")),
                        int(raw.get("total_chunks", 0)),
                        int(raw.get("completed_chunks", 0)),
                        float(raw.get("progress", 0.0)),
                        (str(raw["error"]) if raw.get("error") is not None else None),
                        (str(raw["audio_path"]) if raw.get("audio_path") else None),
                        (str(raw["content_type"]) if raw.get("content_type") else None),
                        (str(raw["filename"]) if raw.get("filename") else None),
                        (str(raw["source_type"]) if raw.get("source_type") else None),
                        (str(raw["source_doc_id"]) if raw.get("source_doc_id") else None),
                        (int(raw["source_chapter_index"]) if raw.get("source_chapter_index") is not None else None),
                        (str(raw["source_chapter_title"]) if raw.get("source_chapter_title") else None),
                        (str(raw["source_book_title"]) if raw.get("source_book_title") else None),
                    ),
                )
            except Exception:
                continue


def _init_data_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    JOBS_DIR.mkdir(parents=True, exist_ok=True)


def _ensure_auth_secret() -> bytes:
    if AUTH_SECRET_FILE.exists():
        text = AUTH_SECRET_FILE.read_text(encoding="utf-8").strip()
        if text:
            return text.encode("utf-8")
    secret_text = secrets.token_urlsafe(48)
    AUTH_SECRET_FILE.write_text(secret_text, encoding="utf-8")
    return secret_text.encode("utf-8")


def _hash_password(password: str, salt_hex: str) -> str:
    salt = bytes.fromhex(salt_hex)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
    return digest.hex()


def _verify_password(password: str, user: UserRecord) -> bool:
    expected = _hash_password(password, user.password_salt)
    return hmac.compare_digest(expected, user.password_hash)


def _create_token(username: str) -> str:
    payload = {"u": username, "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    payload_raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    payload_b64 = _b64url_encode(payload_raw)
    sig = hmac.new(auth_secret, payload_b64.encode("utf-8"), hashlib.sha256).digest()
    return f"{payload_b64}.{_b64url_encode(sig)}"


def _verify_token(token: str) -> str:
    try:
        payload_b64, sig_b64 = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid token format") from exc

    expected_sig = hmac.new(auth_secret, payload_b64.encode("utf-8"), hashlib.sha256).digest()
    try:
        got_sig = _b64url_decode(sig_b64)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid token signature") from exc
    if not hmac.compare_digest(expected_sig, got_sig):
        raise HTTPException(status_code=401, detail="Invalid token signature")

    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid token payload") from exc

    username = str(payload.get("u", "")).strip()
    exp = int(payload.get("exp", 0))
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token user")
    if exp < int(time.time()):
        raise HTTPException(status_code=401, detail="Token expired")
    return username


def _auth_required(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization[7:].strip()
    username = _verify_token(token)
    if _get_user_by_username(username) is None:
        raise HTTPException(status_code=401, detail="User not found")
    return username


def _auth_or_default(authorization: str | None = Header(default=None)) -> str:
    if authorization and authorization.startswith("Bearer "):
        return _auth_required(authorization)
    _ensure_default_local_user()
    return DEFAULT_LOCAL_USER


def _admin_required(current_user: str = Depends(_auth_required)) -> str:
    user = _get_user_by_username(current_user)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privilege required")
    return user.username


def _sanitize_profile_configs(raw: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    clean: dict[str, dict[str, Any]] = {}
    for engine, cfg in (raw or {}).items():
        if engine not in ALLOWED_ENGINES or not isinstance(cfg, dict):
            continue
        out: dict[str, Any] = {}
        for key, value in cfg.items():
            if key not in ALLOWED_CONFIG_KEYS:
                continue
            if key in {"speed"}:
                try:
                    out[key] = float(value)
                except Exception:
                    continue
                continue
            if key in {"api_key", "endpoint", "model", "voice", "instructions", "custom_headers_json", "output_format"}:
                out[key] = str(value) if value is not None else ""
        clean[engine] = out
    return clean


def _row_to_user(row: sqlite3.Row) -> UserRecord:
    return UserRecord(
        username=str(row["username"]),
        password_hash=str(row["password_hash"]),
        password_salt=str(row["password_salt"]),
        created_at=_str_to_dt(str(row["created_at"])),
        tier=str(row["tier"] or "free"),
        is_admin=bool(int(row["is_admin"] or 0)),
        tts_config=_sanitize_profile_configs(json.loads(str(row["tts_config_json"]) or "{}")),
    )


def _row_to_document(row: sqlite3.Row) -> StoredDocument:
    chapters_raw = json.loads(str(row["chapters_json"]) or "[]")
    if not isinstance(chapters_raw, list):
        chapters_raw = []
    chapters = [Chapter(title=str(c["title"]), text=str(c["text"])) for c in chapters_raw if isinstance(c, dict)]
    return StoredDocument(
        id=str(row["id"]),
        owner=str(row["owner"]),
        filename=str(row["filename"]),
        created_at=_str_to_dt(str(row["created_at"])),
        chapters=chapters,
    )


def _row_to_job(row: sqlite3.Row) -> SynthesisJob:
    return SynthesisJob(
        id=str(row["id"]),
        owner=str(row["owner"]),
        status=str(row["status"] or "failed"),
        created_at=_str_to_dt(str(row["created_at"])),
        updated_at=_str_to_dt(str(row["updated_at"])),
        engine=str(row["engine"]),
        output_format=str(row["output_format"] or "mp3"),
        total_chunks=int(row["total_chunks"] or 0),
        completed_chunks=int(row["completed_chunks"] or 0),
        progress=float(row["progress"] or 0.0),
        error=(str(row["error"]) if row["error"] is not None else None),
        audio_path=(str(row["audio_path"]) if row["audio_path"] else None),
        content_type=(str(row["content_type"]) if row["content_type"] else None),
        filename=(str(row["filename"]) if row["filename"] else None),
        source_type=(str(row["source_type"]) if row["source_type"] else None),
        source_doc_id=(str(row["source_doc_id"]) if row["source_doc_id"] else None),
        source_chapter_index=(int(row["source_chapter_index"]) if row["source_chapter_index"] is not None else None),
        source_chapter_title=(str(row["source_chapter_title"]) if row["source_chapter_title"] else None),
        source_book_title=(str(row["source_book_title"]) if row["source_book_title"] else None),
    )


def _save_user(user: UserRecord) -> None:
    _db_exec(
        """
        INSERT OR REPLACE INTO users (
            username, password_hash, password_salt, created_at, tts_config_json, tier, is_admin
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user.username,
            user.password_hash,
            user.password_salt,
            _dt_to_str(user.created_at),
            json.dumps(_sanitize_profile_configs(user.tts_config), ensure_ascii=False),
            user.tier or "free",
            1 if user.is_admin else 0,
        ),
    )


def _get_user_by_username(username: str) -> UserRecord | None:
    row = _db_fetchone(
        """
        SELECT username, password_hash, password_salt, created_at, tier, is_admin, tts_config_json
        FROM users
        WHERE username = ?
        """,
        (username,),
    )
    if not row:
        return None
    user = _row_to_user(row)
    users[user.username] = user
    return user


def _save_users() -> None:
    for u in users.values():
        _save_user(u)


def _load_users() -> None:
    users.clear()
    rows = _db_fetchall(
        "SELECT username, password_hash, password_salt, created_at, tier, is_admin, tts_config_json FROM users"
    )
    for row in rows:
        try:
            user = _row_to_user(row)
            if not user.username.strip():
                continue
            users[user.username] = user
        except Exception:
            continue


def _doc_file(doc_id: str) -> Path:
    return DOCS_DIR / f"{doc_id}.json"


def _save_document(doc: StoredDocument) -> None:
    chapters = [{"title": c.title, "text": c.text} for c in doc.chapters]
    _db_exec(
        """
        INSERT OR REPLACE INTO documents (id, owner, filename, created_at, chapters_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            doc.id,
            doc.owner,
            doc.filename,
            _dt_to_str(doc.created_at),
            json.dumps(chapters, ensure_ascii=False),
        ),
    )


def _load_documents() -> None:
    documents.clear()
    rows = _db_fetchall("SELECT id, owner, filename, created_at, chapters_json FROM documents")
    for row in rows:
        try:
            doc = _row_to_document(row)
            if doc.id and doc.owner:
                documents[doc.id] = doc
        except Exception:
            continue


def _job_file(job_id: str) -> Path:
    return JOBS_DIR / f"{job_id}.json"


def _save_job(job: SynthesisJob) -> None:
    _db_exec(
        """
        INSERT OR REPLACE INTO jobs (
            id, owner, status, created_at, updated_at, engine, output_format,
            total_chunks, completed_chunks, progress, error, audio_path, content_type, filename,
            source_type, source_doc_id, source_chapter_index, source_chapter_title, source_book_title
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job.id,
            job.owner,
            job.status,
            _dt_to_str(job.created_at),
            _dt_to_str(job.updated_at),
            job.engine,
            job.output_format,
            job.total_chunks,
            job.completed_chunks,
            job.progress,
            job.error,
            job.audio_path,
            job.content_type,
            job.filename,
            job.source_type,
            job.source_doc_id,
            job.source_chapter_index,
            job.source_chapter_title,
            job.source_book_title,
        ),
    )


def _delete_job_files(job: SynthesisJob) -> None:
    jf = _job_file(job.id)
    if jf.exists():
        try:
            jf.unlink()
        except OSError:
            pass
    if job.audio_path:
        ap = Path(job.audio_path)
        if ap.exists():
            try:
                ap.unlink()
            except OSError:
                pass


def _delete_job_record(job_id: str) -> None:
    _db_exec("DELETE FROM jobs WHERE id = ?", (job_id,))


def _delete_document_record(doc_id: str, owner: str) -> None:
    _db_exec("DELETE FROM documents WHERE id = ? AND owner = ?", (doc_id, owner))


def _load_jobs() -> None:
    jobs.clear()
    rows = _db_fetchall(
        """
        SELECT id, owner, status, created_at, updated_at, engine, output_format,
               total_chunks, completed_chunks, progress, error, audio_path, content_type, filename,
               source_type, source_doc_id, source_chapter_index, source_chapter_title, source_book_title
        FROM jobs
        """
    )
    for row in rows:
        try:
            status = str(row["status"] or "failed")
            if status in {"queued", "running"}:
                status = "failed"
                restart_error = "Server restarted while job was running"
            else:
                restart_error = None
            job = _row_to_job(row)
            job.status = status
            if restart_error:
                job.error = restart_error
            if job.id and job.owner:
                jobs[job.id] = job
                if restart_error:
                    _save_job(job)
        except Exception:
            continue


def _mark_interrupted_jobs_failed() -> None:
    _db_exec(
        """
        UPDATE jobs
        SET status = 'failed',
            error = 'Server restarted while job was running',
            updated_at = ?
        WHERE status IN ('queued', 'running')
        """,
        (_dt_to_str(_utc_now()),),
    )


def _touch_job(job: SynthesisJob) -> None:
    job.updated_at = _utc_now()
    _save_job(job)


def _job_payload(job: SynthesisJob) -> dict:
    return {
        "job_id": job.id,
        "status": job.status,
        "engine": job.engine,
        "output_format": job.output_format,
        "total_chunks": job.total_chunks,
        "completed_chunks": job.completed_chunks,
        "progress": round(job.progress, 4),
        "error": job.error,
        "created_at": _dt_to_str(job.created_at),
        "updated_at": _dt_to_str(job.updated_at),
        "ready": job.status == "completed",
        "audio_url": f"/api/synthesize_jobs/{job.id}/audio" if job.status == "completed" else None,
        "download_url": f"/api/synthesize_jobs/{job.id}/download" if job.status == "completed" else None,
        "source_type": job.source_type,
        "source_doc_id": job.source_doc_id,
        "source_chapter_index": job.source_chapter_index,
        "source_chapter_title": job.source_chapter_title,
        "source_book_title": job.source_book_title,
        "filename": job.filename,
    }


def _cleanup_jobs() -> None:
    total = _db_count("jobs")
    if total <= MAX_STORED_JOBS:
        return
    rows = _db_fetchall(
        """
        SELECT id, owner, status, created_at, updated_at, engine, output_format,
               total_chunks, completed_chunks, progress, error, audio_path, content_type, filename,
               source_type, source_doc_id, source_chapter_index, source_chapter_title, source_book_title
        FROM jobs
        WHERE status IN ('completed', 'failed')
        ORDER BY updated_at ASC
        """
    )
    candidates = [_row_to_job(r) for r in rows]
    while total > MAX_STORED_JOBS and candidates:
        old = candidates.pop(0)
        jobs.pop(old.id, None)
        _delete_job_record(old.id)
        _delete_job_files(old)
        total -= 1


def _find_existing_job(owner: str, source_meta: dict[str, Any], engine: str, output_format: str) -> SynthesisJob | None:
    if source_meta.get("source_type") != "chapter":
        return None
    source_doc_id = source_meta.get("source_doc_id")
    source_chapter_index = source_meta.get("source_chapter_index")
    candidate_filename = _build_filename_from_source(source_meta, output_format, "custom")
    if source_doc_id is None or source_chapter_index is None:
        return None

    row = _db_fetchone(
        """
        SELECT id, owner, status, created_at, updated_at, engine, output_format,
               total_chunks, completed_chunks, progress, error, audio_path, content_type, filename,
               source_type, source_doc_id, source_chapter_index, source_chapter_title, source_book_title
        FROM jobs
        WHERE owner = ?
          AND engine = ?
          AND lower(output_format) = ?
          AND status IN ('queued', 'running', 'completed')
          AND (
                (source_type = 'chapter' AND source_doc_id = ? AND source_chapter_index = ?)
                OR filename = ?
          )
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (owner, engine, output_format.lower(), source_doc_id, int(source_chapter_index), candidate_filename),
    )
    if not row:
        return None
    job = _row_to_job(row)
    jobs[job.id] = job
    return job


def _get_owned_doc(doc_id: str, owner: str) -> StoredDocument:
    row = _db_fetchone(
        "SELECT id, owner, filename, created_at, chapters_json FROM documents WHERE id = ? AND owner = ?",
        (doc_id, owner),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    doc = _row_to_document(row)
    documents[doc.id] = doc
    return doc


def _resolve_text(req: SynthesizeRequest, owner: str) -> tuple[str, dict[str, Any]]:
    text = (req.custom_text or "").strip()
    if text:
        return text, {
            "source_type": "custom_text",
            "source_doc_id": None,
            "source_chapter_index": None,
            "source_chapter_title": None,
            "source_book_title": None,
        }
    if not req.doc_id or req.chapter_index is None:
        raise HTTPException(status_code=400, detail="Provide custom_text or (doc_id + chapter_index)")

    doc = _get_owned_doc(req.doc_id, owner)
    if req.chapter_index < 0 or req.chapter_index >= len(doc.chapters):
        raise HTTPException(status_code=404, detail="Chapter not found")
    chapter = doc.chapters[req.chapter_index]
    return chapter.text, {
        "source_type": "chapter",
        "source_doc_id": doc.id,
        "source_chapter_index": req.chapter_index,
        "source_chapter_title": chapter.title,
        "source_book_title": Path(doc.filename).stem,
    }


def _apply_profile_config(req: SynthesizeRequest, owner: str) -> dict[str, Any]:
    user = _get_user_by_username(owner)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    profile = user.tts_config.get(req.engine, {})

    def pick_str(value: str | None, key: str) -> str | None:
        if value is not None and str(value).strip() != "":
            return str(value).strip()
        raw = profile.get(key, "")
        return str(raw).strip() if raw else None

    output_format = (str(req.output_format).strip() if req.output_format else "") or str(profile.get("output_format", "mp3"))
    speed = req.speed
    if speed is None and "speed" in profile:
        try:
            speed = float(profile["speed"])
        except Exception:
            speed = 1.0

    return {
        "api_key": pick_str(req.api_key, "api_key"),
        "endpoint": pick_str(req.endpoint, "endpoint"),
        "model": pick_str(req.model, "model"),
        "voice": pick_str(req.voice, "voice"),
        "instructions": pick_str(req.instructions, "instructions"),
        "custom_headers_json": pick_str(req.custom_headers_json, "custom_headers_json"),
        "speed": float(speed if speed is not None else 1.0),
        "output_format": output_format.lower(),
    }


def _prepare_synthesis(req: SynthesizeRequest, owner: str) -> tuple[list[str], dict[str, Any], dict[str, Any]]:
    text, source_meta = _resolve_text(req, owner)
    chunks = split_text_for_tts(text, max_chars=3000)
    if not chunks:
        raise HTTPException(status_code=400, detail="No readable text to synthesize")

    params = _apply_profile_config(req, owner)
    if len(chunks) > 1 and params["output_format"] in {"wav", "flac", "pcm"}:
        raise HTTPException(
            status_code=400,
            detail="Long text with wav/flac/pcm is not supported in merged mode. Use mp3/opus or shorten text.",
        )
    return chunks, params, source_meta


def _job_audio_path(job_id: str, output_format: str) -> Path:
    return AUDIO_DIR / f"{job_id}.{output_format.lower()}"


async def _run_synthesis_job(job_id: str, req: SynthesizeRequest, owner: str, chunks: list[str], params: dict[str, Any]) -> None:
    job = jobs.get(job_id)
    if not job:
        return
    try:
        async with synthesis_semaphore:
            job.status = "running"
            _touch_job(job)

            audio_parts: list[bytes] = []
            total = len(chunks)
            for idx, chunk in enumerate(chunks, start=1):
                audio = await synthesize_text(
                    req.engine,
                    chunk,
                    api_key=params["api_key"],
                    model=params["model"],
                    voice=params["voice"],
                    output_format=params["output_format"],
                    speed=params["speed"],
                    endpoint=params["endpoint"],
                    instructions=params["instructions"],
                    custom_headers_json=params["custom_headers_json"],
                )
                audio_parts.append(audio)
                job.completed_chunks = idx
                job.progress = idx / total
                _touch_job(job)

            merged = b"".join(audio_parts)
            audio_path = _job_audio_path(job.id, params["output_format"])
            audio_path.write_bytes(merged)
            job.audio_path = str(audio_path)
            job.content_type = output_content_type(params["output_format"])
            job.filename = _build_filename_from_source(
                {
                    "source_type": job.source_type,
                    "source_doc_id": job.source_doc_id,
                    "source_chapter_index": job.source_chapter_index,
                    "source_chapter_title": job.source_chapter_title,
                    "source_book_title": job.source_book_title,
                },
                params["output_format"],
                f"custom-{job.id[:8]}",
            )
            job.status = "completed"
            _touch_job(job)
    except Exception as exc:
        job.status = "failed"
        job.error = f"Synthesis failed: {exc}"
        _touch_job(job)
    finally:
        _cleanup_jobs()


def _read_job_audio(job: SynthesisJob) -> bytes:
    if not job.audio_path:
        raise HTTPException(status_code=409, detail="Audio is not ready")
    path = Path(job.audio_path)
    if not path.exists():
        raise HTTPException(status_code=409, detail="Audio file is missing")
    return path.read_bytes()


@app.on_event("startup")
async def startup_event():
    global auth_secret, db_conn
    _init_data_dirs()
    db_conn = _db_connect()
    _init_db()
    if ENABLE_MEMBERSHIP:
        _seed_default_plans()
    _migrate_legacy_json_data_if_needed()
    if ENABLE_MEMBERSHIP:
        _ensure_admin_exists()
    _mark_interrupted_jobs_failed()
    auth_secret = _ensure_auth_secret()
    _ensure_default_local_user()
    users.clear()
    documents.clear()
    jobs.clear()


@app.on_event("shutdown")
async def shutdown_event():
    global db_conn
    if db_conn is not None:
        with db_lock:
            db_conn.close()
        db_conn = None


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/auth/register")
async def register(req: AuthRequest):
    if not ENABLE_SIGNUP:
        raise HTTPException(status_code=403, detail="Signup is disabled")

    username = req.username.strip()
    password = req.password
    if not USERNAME_RE.match(username):
        raise HTTPException(status_code=400, detail="Username must be 3-32 chars: letters, numbers, _ . -")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if _get_user_by_username(username) is not None:
        raise HTTPException(status_code=409, detail="Username already exists")

    salt_hex = secrets.token_hex(16)
    is_first_admin = _db_fetchone("SELECT username FROM users WHERE is_admin = 1 LIMIT 1") is None
    user = UserRecord(
        username=username,
        password_hash=_hash_password(password, salt_hex),
        password_salt=salt_hex,
        created_at=_utc_now(),
        tier="free",
        is_admin=is_first_admin,
        tts_config={},
    )
    users[username] = user
    _save_user(user)
    return {"username": username, "token": _create_token(username), "tier": user.tier, "is_admin": user.is_admin}


@app.post("/api/auth/login")
async def login(req: AuthRequest):
    username = req.username.strip()
    user = _get_user_by_username(username)
    if not user or not _verify_password(req.password, user):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"username": username, "token": _create_token(username), "tier": user.tier, "is_admin": user.is_admin}


@app.get("/api/auth/me")
async def me(current_user: str = Depends(_auth_required)):
    user = _get_user_by_username(current_user)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return {
        "username": user.username,
        "created_at": _dt_to_str(user.created_at),
        "tier": user.tier,
        "is_admin": user.is_admin,
    }


@app.get("/api/profile/tts_config")
async def get_profile_tts_config(current_user: str = Depends(_auth_required)):
    user = _get_user_by_username(current_user)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return {"configs": user.tts_config}


@app.put("/api/profile/tts_config")
async def put_profile_tts_config(req: ProfileConfigRequest, current_user: str = Depends(_auth_required)):
    user = _get_user_by_username(current_user)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    user.tts_config = _sanitize_profile_configs(req.configs)
    users[current_user] = user
    _save_user(user)
    return {"ok": True, "configs": user.tts_config}


@app.get("/api/quota")
async def get_quota(current_user: str = Depends(_auth_or_default)):
    user = _get_user_by_username(current_user)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return _quota_payload_for_user(user)


@app.get("/api/plans")
async def list_plans(_current_user: str = Depends(_auth_required)):
    _membership_feature_required()
    rows = _db_fetchall(
        """
        SELECT tier, display_name, max_uploads_month, max_syntheses_month, sort_order
        FROM membership_plans
        ORDER BY sort_order ASC, tier ASC
        """
    )
    return {
        "plans": [
            {
                "tier": str(r["tier"]),
                "display_name": str(r["display_name"]),
                "max_uploads_month": int(r["max_uploads_month"]),
                "max_syntheses_month": int(r["max_syntheses_month"]),
                "sort_order": int(r["sort_order"]),
            }
            for r in rows
        ]
    }


@app.get("/api/admin/plans")
async def admin_list_plans(_admin_user: str = Depends(_admin_required)):
    _membership_feature_required()
    return await list_plans(_admin_user)


@app.put("/api/admin/plans/{tier}")
async def admin_update_plan(tier: str, req: PlanUpdateRequest, _admin_user: str = Depends(_admin_required)):
    _membership_feature_required()
    tier_norm = tier.strip().lower()
    if not tier_norm:
        raise HTTPException(status_code=400, detail="Tier is required")
    row = _db_fetchone("SELECT tier, display_name FROM membership_plans WHERE tier = ?", (tier_norm,))
    if not row:
        raise HTTPException(status_code=404, detail="Plan not found")
    uploads = _normalize_limit(req.max_uploads_month)
    synths = _normalize_limit(req.max_syntheses_month)
    display_name = (req.display_name or str(row["display_name"])).strip() or str(row["display_name"])
    _db_exec(
        """
        UPDATE membership_plans
        SET display_name = ?, max_uploads_month = ?, max_syntheses_month = ?
        WHERE tier = ?
        """,
        (display_name, uploads, synths, tier_norm),
    )
    return {"ok": True, "tier": tier_norm}


@app.get("/api/admin/users")
async def admin_list_users(_admin_user: str = Depends(_admin_required)):
    _membership_feature_required()
    ym = _current_month_key()
    rows = _db_fetchall(
        """
        SELECT u.username, u.created_at, u.tier, u.is_admin,
               p.display_name, p.max_uploads_month, p.max_syntheses_month,
               COALESCE(m.upload_count, 0) AS upload_count,
               COALESCE(m.synth_count, 0) AS synth_count
        FROM users u
        LEFT JOIN membership_plans p ON p.tier = u.tier
        LEFT JOIN usage_monthly m ON m.username = u.username AND m.ym = ?
        ORDER BY u.created_at ASC
        """,
        (ym,),
    )
    users_out = []
    for r in rows:
        up_limit = int(r["max_uploads_month"]) if r["max_uploads_month"] is not None else -1
        sy_limit = int(r["max_syntheses_month"]) if r["max_syntheses_month"] is not None else -1
        up_used = int(r["upload_count"] or 0)
        sy_used = int(r["synth_count"] or 0)
        users_out.append(
            {
                "username": str(r["username"]),
                "created_at": str(r["created_at"]),
                "tier": str(r["tier"] or "free"),
                "tier_display_name": str(r["display_name"] or r["tier"] or "free"),
                "is_admin": bool(int(r["is_admin"] or 0)),
                "usage": {"uploads_month": up_used, "syntheses_month": sy_used},
                "limits": {"uploads_month": up_limit, "syntheses_month": sy_limit},
                "remaining": {
                    "uploads_month": (-1 if up_limit < 0 else max(up_limit - up_used, 0)),
                    "syntheses_month": (-1 if sy_limit < 0 else max(sy_limit - sy_used, 0)),
                },
            }
        )
    return {"month": ym, "users": users_out}


@app.put("/api/admin/users/{username}/tier")
async def admin_update_user_tier(
    username: str, req: UserTierUpdateRequest, _admin_user: str = Depends(_admin_required)
):
    _membership_feature_required()
    username_norm = username.strip()
    if not username_norm:
        raise HTTPException(status_code=400, detail="Username is required")
    user = _get_user_by_username(username_norm)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    tier = req.tier.strip().lower()
    plan = _db_fetchone("SELECT tier FROM membership_plans WHERE tier = ?", (tier,))
    if not plan:
        raise HTTPException(status_code=400, detail="Invalid tier")
    user.tier = tier
    users[user.username] = user
    _save_user(user)
    return {"ok": True, "username": user.username, "tier": user.tier}


@app.get("/api/engines")
async def list_engines(_current_user: str = Depends(_auth_or_default)):
    return {
        "engines": [
            {
                "id": "openai",
                "name": "OpenAI TTS (ChatGPT API)",
                "defaults": {"model": "gpt-4o-mini-tts", "voice": "alloy", "output_format": "mp3", "speed": 1.0},
            },
            {
                "id": "edge_tts",
                "name": "Edge TTS (No API key)",
                "defaults": {"voice": "zh-CN-XiaoxiaoNeural", "output_format": "mp3", "speed": 1.0},
            },
            {
                "id": "custom_http",
                "name": "Custom HTTP TTS API",
                "defaults": {"output_format": "mp3", "speed": 1.0},
            },
        ]
    }


@app.get("/api/voices")
async def list_voices(engine: EngineType, _current_user: str = Depends(_auth_or_default)):
    try:
        voices = await list_engine_voices(engine)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to load voices: {exc}") from exc
    return {"engine": engine, "voices": voices}


@app.post("/api/upload_epub")
async def upload_epub(file: UploadFile = File(...), current_user: str = Depends(_auth_or_default)):
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in {".epub", ".pdf", ".txt", ".doc", ".docx"}:
        raise HTTPException(status_code=400, detail="Only .epub, .pdf, .txt, .docx are supported")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="File is empty")

    try:
        chapters = parse_document_bytes(data, original_name=filename)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse document: {exc}") from exc

    if not chapters:
        raise HTTPException(status_code=400, detail="No readable text extracted from document")

    doc_id = uuid.uuid4().hex
    doc = StoredDocument(
        id=doc_id,
        owner=current_user,
        filename=filename,
        created_at=_utc_now(),
        chapters=chapters,
    )
    _consume_quota(current_user, "upload")
    documents[doc_id] = doc
    _save_document(doc)
    return {
        "doc_id": doc_id,
        "filename": filename,
        "chapter_count": len(chapters),
        "chapters": chapter_preview(chapters),
    }


@app.get("/api/documents")
async def list_documents(limit: int = 100, current_user: str = Depends(_auth_or_default)):
    if limit < 1:
        limit = 1
    if limit > 500:
        limit = 500
    rows = _db_fetchall(
        """
        SELECT id, owner, filename, created_at, chapters_json
        FROM documents
        WHERE owner = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (current_user, limit),
    )
    out: list[dict[str, Any]] = []
    for r in rows:
        try:
            chapters = json.loads(str(r["chapters_json"]) or "[]")
            chapter_count = len(chapters) if isinstance(chapters, list) else 0
        except Exception:
            chapter_count = 0
        out.append(
            {
                "doc_id": str(r["id"]),
                "filename": str(r["filename"]),
                "created_at": str(r["created_at"]),
                "chapter_count": chapter_count,
            }
        )
    return {"documents": out}


@app.get("/api/documents/{doc_id}")
async def get_document(doc_id: str, current_user: str = Depends(_auth_or_default)):
    doc = _get_owned_doc(doc_id, current_user)
    return {
        "doc_id": doc.id,
        "filename": doc.filename,
        "created_at": _dt_to_str(doc.created_at),
        "chapter_count": len(doc.chapters),
        "chapters": chapter_preview(doc.chapters),
    }


@app.get("/api/documents/{doc_id}/chapters/{chapter_index}")
async def get_chapter(doc_id: str, chapter_index: int, current_user: str = Depends(_auth_or_default)):
    doc = _get_owned_doc(doc_id, current_user)
    if chapter_index < 0 or chapter_index >= len(doc.chapters):
        raise HTTPException(status_code=404, detail="Chapter not found")
    ch = doc.chapters[chapter_index]
    return {"index": chapter_index, "title": ch.title, "text": ch.text, "length": len(ch.text)}


@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str, current_user: str = Depends(_auth_or_default)):
    doc = _get_owned_doc(doc_id, current_user)
    documents.pop(doc.id, None)
    _delete_document_record(doc.id, current_user)
    return {"ok": True, "doc_id": doc.id, "filename": doc.filename}


@app.post("/api/synthesize")
async def synthesize(req: SynthesizeRequest, current_user: str = Depends(_auth_or_default)):
    chunks, params, source_meta = _prepare_synthesis(req, current_user)
    _consume_quota(current_user, "synthesize")
    try:
        audio_parts: list[bytes] = []
        for chunk in chunks:
            audio = await synthesize_text(
                req.engine,
                chunk,
                api_key=params["api_key"],
                model=params["model"],
                voice=params["voice"],
                output_format=params["output_format"],
                speed=params["speed"],
                endpoint=params["endpoint"],
                instructions=params["instructions"],
                custom_headers_json=params["custom_headers_json"],
            )
            audio_parts.append(audio)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Synthesis failed: {exc}") from exc

    merged = b"".join(audio_parts)
    content_type = output_content_type(params["output_format"])
    filename = _build_filename_from_source(source_meta, params["output_format"], f"custom-{uuid.uuid4().hex[:8]}")
    headers = {
        "Content-Disposition": _content_disposition_value(filename, attachment=False),
        "X-Chunks": str(len(audio_parts)),
    }
    return Response(content=merged, media_type=content_type, headers=headers)


@app.post("/api/synthesize_jobs")
async def create_synthesize_job(req: SynthesizeRequest, current_user: str = Depends(_auth_or_default)):
    chunks, params, source_meta = _prepare_synthesis(req, current_user)
    existing = _find_existing_job(current_user, source_meta, req.engine, params["output_format"])
    if existing and not req.force_resynthesize:
        payload = _job_payload(existing)
        payload["already_exists"] = True
        payload["message"] = "该章节已合成过，已复用历史任务"
        return payload

    _consume_quota(current_user, "synthesize")
    job_id = uuid.uuid4().hex
    now = _utc_now()
    job = SynthesisJob(
        id=job_id,
        owner=current_user,
        status="queued",
        created_at=now,
        updated_at=now,
        engine=req.engine,
        output_format=params["output_format"],
        total_chunks=len(chunks),
        completed_chunks=0,
        progress=0.0,
        error=None,
        audio_path=None,
        content_type=None,
        filename=_build_filename_from_source(source_meta, params["output_format"], f"custom-{job_id[:8]}"),
        source_type=source_meta["source_type"],
        source_doc_id=source_meta["source_doc_id"],
        source_chapter_index=source_meta["source_chapter_index"],
        source_chapter_title=source_meta["source_chapter_title"],
        source_book_title=source_meta["source_book_title"],
    )
    jobs[job_id] = job
    _save_job(job)
    _cleanup_jobs()
    asyncio.create_task(_run_synthesis_job(job_id, req, current_user, chunks, params))
    return _job_payload(job)


@app.get("/api/synthesize_jobs")
async def list_synthesis_jobs(
    limit: int = 50,
    completed_only: bool = False,
    current_user: str = Depends(_auth_or_default),
):
    if limit < 1:
        limit = 1
    if limit > 200:
        limit = 200

    query = """
        SELECT id, owner, status, created_at, updated_at, engine, output_format,
               total_chunks, completed_chunks, progress, error, audio_path, content_type, filename,
               source_type, source_doc_id, source_chapter_index, source_chapter_title, source_book_title
        FROM jobs
        WHERE owner = ?
    """
    params: list[Any] = [current_user]
    if completed_only:
        query += " AND status = 'completed'"
    query += " ORDER BY updated_at DESC LIMIT ?"
    params.append(limit)
    rows = _db_fetchall(query, tuple(params))
    out: list[dict[str, Any]] = []
    for row in rows:
        job = _row_to_job(row)
        jobs[job.id] = job
        out.append(_job_payload(job))
    return {"jobs": out}


def _get_owned_job(job_id: str, owner: str) -> SynthesisJob:
    row = _db_fetchone(
        """
        SELECT id, owner, status, created_at, updated_at, engine, output_format,
               total_chunks, completed_chunks, progress, error, audio_path, content_type, filename,
               source_type, source_doc_id, source_chapter_index, source_chapter_title, source_book_title
        FROM jobs
        WHERE id = ? AND owner = ?
        """,
        (job_id, owner),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    job = _row_to_job(row)
    jobs[job.id] = job
    return job


@app.get("/api/synthesize_jobs/{job_id}")
async def get_synthesize_job(job_id: str, current_user: str = Depends(_auth_or_default)):
    job = _get_owned_job(job_id, current_user)
    return _job_payload(job)


@app.get("/api/synthesize_jobs/{job_id}/audio")
async def get_synthesize_job_audio(job_id: str, current_user: str = Depends(_auth_or_default)):
    job = _get_owned_job(job_id, current_user)
    if job.status != "completed":
        raise HTTPException(status_code=409, detail="Audio is not ready")
    content = _read_job_audio(job)
    filename = job.filename or f"custom-{job.id[:8]}.{job.output_format}"
    headers = {
        "Content-Disposition": _content_disposition_value(filename, attachment=False),
        "X-Chunks": str(job.total_chunks),
    }
    return Response(content=content, media_type=job.content_type or "application/octet-stream", headers=headers)


@app.get("/api/synthesize_jobs/{job_id}/download")
async def download_synthesize_job_audio(job_id: str, current_user: str = Depends(_auth_or_default)):
    job = _get_owned_job(job_id, current_user)
    if job.status != "completed":
        raise HTTPException(status_code=409, detail="Audio is not ready")
    content = _read_job_audio(job)
    filename = job.filename or f"custom-{job.id[:8]}.{job.output_format}"
    headers = {
        "Content-Disposition": _content_disposition_value(filename, attachment=True),
        "X-Chunks": str(job.total_chunks),
    }
    return Response(content=content, media_type=job.content_type or "application/octet-stream", headers=headers)


@app.delete("/api/synthesize_jobs/{job_id}")
async def delete_synthesize_job(job_id: str, current_user: str = Depends(_auth_or_default)):
    job = _get_owned_job(job_id, current_user)
    if job.status in {"queued", "running"}:
        raise HTTPException(status_code=409, detail="Job is still running and cannot be deleted")
    jobs.pop(job.id, None)
    _delete_job_record(job.id)
    _delete_job_files(job)
    return {"ok": True, "job_id": job.id}
