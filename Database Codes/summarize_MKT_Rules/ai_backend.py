"""ai_backend.py — pluggable AI client for the Market-Rules summarizers.

The summarize_* scripts and gen_stakeholder_sections.py all talk to Claude
through a tiny client object:

    msg = get_client().messages.create(model=..., max_tokens=..., **sys, messages=[...])
    text = msg.content[0].text
    msg.usage.input_tokens / msg.usage.output_tokens

This module returns a client whose `.messages.create()` honours that exact
contract but dispatches to one of two backends, chosen by the environment:

    POWERTALKS_AI_BACKEND = "api"   -> paid, metered Anthropic API (SDK).
                                       Preserves the glossary prompt cache.
                                       Use for one-off bulk backfills.
    POWERTALKS_AI_BACKEND = "cli"   -> local `claude.exe` headless (-p), billed
              (default)              against the logged-in Claude subscription,
                                       not the metered API. Use for the nightly
                                       incremental refresh.

Backend selection is read once, when the singleton client is first created.

CLI notes:
  * The glossary `system` block is 130k+ chars — far past the Windows command
    line limit — so the CLI backend folds system + user text into one prompt
    piped over stdin (`claude -p` reads stdin as the prompt), never argv.
  * `--output-format json` returns one JSON object; we read `.result` for the
    text and `.usage` for token counts (0 if the CLI omits them).
  * `--max-turns 1` keeps it a single text turn (no tool loops / no hangs).

Env overrides:
  POWERTALKS_AI_BACKEND   api | cli            (default: cli)
  POWERTALKS_CLAUDE_EXE   path to claude.exe   (default: %USERPROFILE%\\.local\\bin\\claude.exe)
  POWERTALKS_CLI_TIMEOUT  per-call seconds     (default: 180)
"""

import json
import os
import subprocess

DEFAULT_CLAUDE_EXE = os.path.join(
    os.environ.get("USERPROFILE", r"C:\Users\chunl"), ".local", "bin", "claude.exe"
)


# ─── response shims (mimic the anthropic SDK objects the scripts read) ────────
class _Usage:
    __slots__ = ("input_tokens", "output_tokens")

    def __init__(self, i, o):
        self.input_tokens = i
        self.output_tokens = o


class _Block:
    __slots__ = ("text",)

    def __init__(self, text):
        self.text = text


class _Msg:
    def __init__(self, text, in_tok, out_tok):
        self.content = [_Block(text)]
        self.usage = _Usage(in_tok, out_tok)


# ─── prompt flattening (system + messages -> one stdin string, CLI backend) ───
def _text_of(block):
    if isinstance(block, dict):
        return block.get("text", "")
    return getattr(block, "text", str(block))


def _flatten_system(system):
    if not system:
        return ""
    if isinstance(system, str):
        return system
    return "\n".join(_text_of(b) for b in system)


def _flatten_messages(messages):
    parts = []
    for m in messages:
        c = m.get("content")
        if isinstance(c, str):
            parts.append(c)
        elif isinstance(c, list):
            parts.extend(_text_of(b) for b in c)
    return "\n\n".join(parts)


def _model_alias(model):
    m = (model or "").lower()
    if "haiku" in m:
        return "haiku"
    if "sonnet" in m:
        return "sonnet"
    if "opus" in m:
        return "opus"
    return model


# ─── backends ─────────────────────────────────────────────────────────────────
class _ApiMessages:
    def __init__(self, parent):
        self._p = parent

    def create(self, *, model, max_tokens, messages, system=None, **kw):
        client = self._p._api()
        call = {"model": model, "max_tokens": max_tokens, "messages": messages}
        if system is not None:
            call["system"] = system          # keep cache_control blocks intact
        call.update(kw)
        return client.messages.create(**call)  # native SDK message (content/usage)


class _CliMessages:
    def __init__(self, parent):
        self._p = parent

    def create(self, *, model, max_tokens, messages, system=None, **kw):
        prompt_parts = []
        sys_txt = _flatten_system(system)
        if sys_txt:
            prompt_parts.append(sys_txt)
        prompt_parts.append(_flatten_messages(messages))
        prompt_parts.append(
            "Respond with only the requested text. Do not use any tools, "
            "and do not add any preamble or explanation."
        )
        prompt = "\n\n".join(prompt_parts)

        cmd = [
            self._p.exe, "-p",
            "--model", _model_alias(model),
            "--output-format", "json",
            "--max-turns", "1",
        ]
        proc = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=self._p.timeout,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"claude CLI exited {proc.returncode}: "
                f"{(proc.stderr or proc.stdout or '').strip()[:300]}"
            )
        try:
            data = json.loads(proc.stdout)
        except ValueError as e:
            raise RuntimeError(
                f"claude CLI did not return JSON: {proc.stdout.strip()[:300]}"
            ) from e
        if data.get("is_error"):
            raise RuntimeError(f"claude CLI error result: {str(data)[:300]}")
        text = (data.get("result") or "").strip()
        usage = data.get("usage") or {}
        in_tok = int(usage.get("input_tokens", 0) or 0)
        out_tok = int(usage.get("output_tokens", 0) or 0)
        return _Msg(text, in_tok, out_tok)


class Client:
    def __init__(self):
        self.mode = os.environ.get("POWERTALKS_AI_BACKEND", "cli").strip().lower()
        self.exe = os.environ.get("POWERTALKS_CLAUDE_EXE", DEFAULT_CLAUDE_EXE)
        self.timeout = int(os.environ.get("POWERTALKS_CLI_TIMEOUT", "180"))
        self._api_client = None
        if self.mode == "api":
            self.messages = _ApiMessages(self)
        else:
            self.mode = "cli"
            self.messages = _CliMessages(self)

    def _api(self):
        if self._api_client is None:
            import anthropic
            from anthropic_key import get_anthropic_key
            self._api_client = anthropic.Anthropic(api_key=get_anthropic_key())
        return self._api_client


_client = None


def get_client():
    """Singleton AI client for the selected backend (read from the env once)."""
    global _client
    if _client is None:
        _client = Client()
    return _client
