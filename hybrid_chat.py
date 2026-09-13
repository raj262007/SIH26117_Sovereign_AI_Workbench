#!/usr/bin/env python3
"""
Hierarchical Hybrid Context Engine — Apple Silicon (MLX)
========================================================
A production-ready, self-contained multi-tier chat system built on mlx-lm.

Tiers:
  0 — Hot Buffer   : Bounded RotatingKVCache (2048 tokens, 4 attention sinks)
  3 — Permanent    : SQLite full history + session summaries

Run:  python hybrid_chat.py
"""

import os
import sys
import uuid
import sqlite3
import textwrap
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import mlx.core as mx
from mlx_lm import load, stream_generate
from mlx_lm.models.cache import KVCache, RotatingKVCache

# ──────────────────────────── Configuration ──────────────────────────────────

MODEL_PATH = "mlx-community/Qwen3.5-4B-OptiQ-4bit"
MAX_KV_SIZE = 2048          # Rotating KV cache budget (tokens)
SINK_TOKENS = 4             # Attention-sink tokens preserved by RotatingKVCache
MAX_GEN_TOKENS = 2048       # Maximum tokens per assistant turn
ACTIVE_TURNS = 8            # Keep last N messages in the prompt (4 user + 4 asst)
SUMMARIZE_EVERY = 6         # Trigger summarization every N new turns
DB_PATH = Path("chat_history.db")

SYSTEM_PROMPT = textwrap.dedent("""\
    You are a concise, direct assistant. Output the answer immediately \
    without internal scratchpads, planning steps, or thinking blocks. \
    Do not use <think> tags or "Thinking Process:" headers."""
).strip()


# ──────────────────────────── SQLite Layer (Tier 3) ──────────────────────────

def init_db(db_path: Path) -> sqlite3.Connection:
    """Create (or open) the SQLite database and ensure the schema exists."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")  # Faster concurrent reads
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS messages (
            id        INTEGER PRIMARY KEY,
            session_id TEXT    NOT NULL,
            role       TEXT    NOT NULL,
            content    TEXT    NOT NULL,
            timestamp  DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS session_summaries (
            session_id TEXT PRIMARY KEY,
            summary    TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_messages_session
            ON messages(session_id, id);
    """)
    conn.commit()
    return conn


def save_message(conn: sqlite3.Connection, session_id: str, role: str, content: str):
    """Persist a single message to SQLite."""
    conn.execute(
        "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
        (session_id, role, content),
    )
    conn.commit()


def load_session_messages(conn: sqlite3.Connection, session_id: str) -> list[dict]:
    """Load the full message history for a session (oldest-first)."""
    rows = conn.execute(
        "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id",
        (session_id,),
    ).fetchall()
    return [{"role": r, "content": c} for r, c in rows]


def get_session_summary(conn: sqlite3.Connection, session_id: str) -> Optional[str]:
    """Retrieve the current session summary, if any."""
    row = conn.execute(
        "SELECT summary FROM session_summaries WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    return row[0] if row else None


def upsert_session_summary(conn: sqlite3.Connection, session_id: str, summary: str):
    """Insert or update the summary for a session."""
    conn.execute(
        """INSERT INTO session_summaries (session_id, summary, updated_at)
           VALUES (?, ?, CURRENT_TIMESTAMP)
           ON CONFLICT(session_id) DO UPDATE SET
               summary = excluded.summary,
               updated_at = excluded.updated_at""",
        (session_id, summary),
    )
    conn.commit()


# ──────────────────────────── Cache Construction ─────────────────────────────

def make_hybrid_cache(model, max_kv_size: int = MAX_KV_SIZE) -> list:
    """
    Build a cache list respecting Qwen3.5's hybrid architecture:
      - Linear-attention layers → native ArraysCache (inherently bounded)
      - Standard-attention layers → RotatingKVCache with attention sinks

    This avoids calling model.make_cache() + losing max_kv_size support.
    """
    lm = model.language_model if hasattr(model, "language_model") else model
    base_cache = lm.make_cache()

    for i, cache_entry in enumerate(base_cache):
        # Replace only unbounded KVCache entries with bounded rotating ones.
        # ArraysCache (linear layers) stays unchanged — it's already O(1) memory.
        if isinstance(cache_entry, KVCache) and not isinstance(cache_entry, RotatingKVCache):
            base_cache[i] = RotatingKVCache(max_size=max_kv_size, keep=SINK_TOKENS)

    return base_cache


# ──────────────────────────── Prompt Assembly ────────────────────────────────

def build_system_prompt(summary: Optional[str]) -> str:
    """Compose the system prompt, injecting the conversation summary if present."""
    parts = [SYSTEM_PROMPT]
    if summary:
        parts.append(f"\nConversation Summary so far:\n{summary}")
    return "\n".join(parts)


def build_prompt_messages(
    all_messages: list[dict],
    summary: Optional[str],
) -> list[dict]:
    """
    Assemble the prompt message list:
      1. System prompt (with optional summary injection)
      2. Last ACTIVE_TURNS messages (keeps context manageable)
    """
    system_msg = {"role": "system", "content": build_system_prompt(summary)}

    # Keep only the most recent turns to stay within the KV budget
    recent = all_messages[-ACTIVE_TURNS:] if len(all_messages) > ACTIVE_TURNS else all_messages
    return [system_msg] + recent


# ──────────────────────────── Background Summarizer ──────────────────────────

def summarize_older_turns(
    model,
    tokenizer,
    older_messages: list[dict],
) -> str:
    """
    Run a quick auxiliary completion to produce a 2-3 bullet summary
    of the older (evicted) messages.
    """
    # Format the older messages into a readable block
    lines = []
    for msg in older_messages:
        prefix = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{prefix}: {msg['content']}")
    conversation_block = "\n".join(lines)

    summarize_prompt_msgs = [
        {
            "role": "system",
            "content": (
                "You are a summarization engine. Given a conversation excerpt, "
                "produce a concise summary in exactly 2-3 bullet points. "
                "Output ONLY the bullet points, nothing else."
            ),
        },
        {
            "role": "user",
            "content": f"Summarize this conversation:\n\n{conversation_block}",
        },
    ]

    prompt_text = tokenizer.apply_chat_template(
        summarize_prompt_msgs,
        add_generation_prompt=True,
        tokenize=False,
        enable_thinking=False,
    )

    # Use a fresh (unbounded) cache for the summarization call
    summary_parts = []
    for resp in stream_generate(
        model, tokenizer, prompt_text, max_tokens=256,
    ):
        summary_parts.append(resp.text)

    return "".join(summary_parts).strip()


def maybe_trigger_summarization(
    model,
    tokenizer,
    conn: sqlite3.Connection,
    session_id: str,
    all_messages: list[dict],
    turn_counter: int,
) -> Optional[str]:
    """
    Every SUMMARIZE_EVERY turns, summarize the older (evicted) messages
    and persist the summary. Returns the updated summary or None.
    """
    if turn_counter % SUMMARIZE_EVERY != 0 or turn_counter == 0:
        return get_session_summary(conn, session_id)

    # Only summarize messages that won't be in the active prompt window
    if len(all_messages) <= ACTIVE_TURNS:
        return get_session_summary(conn, session_id)

    older = all_messages[:-ACTIVE_TURNS]
    print("\n  ⏳ Generating background summary of older turns...", flush=True)

    summary = summarize_older_turns(model, tokenizer, older)
    upsert_session_summary(conn, session_id, summary)
    print("  ✅ Summary updated.\n", flush=True)

    return summary


# ──────────────────────────── Main Chat Loop ─────────────────────────────────

def main():
    # --- Load model and tokenizer ---
    print(f"Loading model: {MODEL_PATH}")
    model, tokenizer = load(MODEL_PATH)
    print("Model loaded.\n")

    # --- Database ---
    conn = init_db(DB_PATH)
    session_id = uuid.uuid4().hex[:12]
    print(f"Session: {session_id}  |  History: {DB_PATH.resolve()}")
    print("Type 'q' or 'exit' to quit. Ctrl+C for graceful exit.\n")

    # --- State ---
    prompt_cache = make_hybrid_cache(model)
    all_messages: list[dict] = []    # In-memory mirror of DB for this session
    turn_counter = 0                 # Counts user+assistant pairs
    current_summary: Optional[str] = None

    try:
        while True:
            # --- Read user input ---
            try:
                user_input = input("You: ").strip()
            except EOFError:
                break

            if not user_input:
                continue
            if user_input.lower() in ("q", "exit"):
                break

            # --- Persist & track the user message ---
            all_messages.append({"role": "user", "content": user_input})
            save_message(conn, session_id, "user", user_input)

            # --- Assemble the prompt ---
            prompt_msgs = build_prompt_messages(all_messages, current_summary)
            prompt_text = tokenizer.apply_chat_template(
                prompt_msgs,
                add_generation_prompt=True,
                tokenize=False,
                enable_thinking=False,
            )

            # --- Rebuild the cache each turn ---
            # Because we re-encode the full prompt window (system + last 8 turns),
            # a fresh bounded cache avoids stale KV entries from prior prompts.
            prompt_cache = make_hybrid_cache(model)

            # --- Stream the response ---
            print("Assistant: ", end="", flush=True)

            response_parts: list[str] = []
            last_resp = None

            for resp in stream_generate(
                model,
                tokenizer,
                prompt_text,
                max_tokens=MAX_GEN_TOKENS,
                prompt_cache=prompt_cache,
            ):
                print(resp.text, end="", flush=True)
                response_parts.append(resp.text)
                last_resp = resp

            print()  # Newline after streamed output

            # --- Metrics ---
            if last_resp is not None:
                print(
                    f"  [{last_resp.generation_tokens} tokens | "
                    f"prompt {last_resp.prompt_tps:.1f} t/s | "
                    f"gen {last_resp.generation_tps:.1f} t/s | "
                    f"peak {last_resp.peak_memory:.2f} GB]"
                )

            # --- Persist & track the assistant response ---
            assistant_text = "".join(response_parts).strip()
            all_messages.append({"role": "assistant", "content": assistant_text})
            save_message(conn, session_id, "assistant", assistant_text)

            # --- Summarization check ---
            turn_counter += 1
            current_summary = maybe_trigger_summarization(
                model, tokenizer, conn, session_id, all_messages, turn_counter,
            )

    except KeyboardInterrupt:
        print("\n\nInterrupted — exiting gracefully.")

    finally:
        conn.close()
        print(f"Session {session_id} saved. Goodbye!")


if __name__ == "__main__":
    main()
