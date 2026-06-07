"""Claude Code skill registry: symlink ~/.emoo/skills/ → ~/.claude/skills/emoo/."""

import os
import shutil
from glob import glob
from pathlib import Path

EMOO_SKILLS_BASE = os.path.expanduser("~/.emoo/skills")
CLAUDE_SKILLS_DIR = os.path.expanduser("~/.claude/skills")
CLAUDE_EMOO_LINK = os.path.join(CLAUDE_SKILLS_DIR, "emoo")

# Package examples directory (relative to this file)
_EXAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "examples")


def _get_api_prefix() -> str:
    """Get current workspace API key prefix for namespace isolation."""
    import json as _json
    config_path = os.path.expanduser("~/.emoo/config.json")
    try:
        with open(config_path) as f:
            cfg = _json.load(f)
        return (cfg.get("api_key") or cfg.get("client_id", "default"))[:12]
    except Exception:
        return "default"


def get_skills_dir() -> str:
    """Get the workspace-specific skills directory."""
    ns_dir = os.path.join(EMOO_SKILLS_BASE, _get_api_prefix())
    os.makedirs(ns_dir, exist_ok=True)
    # Also create legacy dir for backward compat
    if not os.path.isdir(EMOO_SKILLS_BASE):
        os.makedirs(EMOO_SKILLS_BASE, exist_ok=True)
    return ns_dir


def is_registered() -> bool:
    """Check if emoo skills are already registered in Claude Code."""
    if os.path.islink(CLAUDE_EMOO_LINK):
        target = os.readlink(CLAUDE_EMOO_LINK)
        return os.path.samefile(target, get_skills_dir()) if os.path.exists(target) else False
    if os.path.isdir(CLAUDE_EMOO_LINK):
        return os.path.samefile(CLAUDE_EMOO_LINK, get_skills_dir())
    return False


def register_symlink() -> tuple[bool, str]:
    """Create symlink ~/.claude/skills/emoo → ~/.emoo/skills/.

    Returns (success, message).
    """
    os.makedirs(get_skills_dir(), exist_ok=True)
    os.makedirs(CLAUDE_SKILLS_DIR, exist_ok=True)

    if os.path.islink(CLAUDE_EMOO_LINK):
        current = os.readlink(CLAUDE_EMOO_LINK)
        if os.path.exists(current) and os.path.samefile(current, get_skills_dir()):
            return True, f"已注册: {CLAUDE_EMOO_LINK} → {get_skills_dir()}"
        os.unlink(CLAUDE_EMOO_LINK)
    elif os.path.isdir(CLAUDE_EMOO_LINK):
        if os.path.samefile(CLAUDE_EMOO_LINK, get_skills_dir()):
            return True, f"已注册: {CLAUDE_EMOO_LINK} (目录模式)"
        return False, f"{CLAUDE_EMOO_LINK} 已存在但不是指向 {get_skills_dir()}，请手动处理"
    elif os.path.exists(CLAUDE_EMOO_LINK):
        os.unlink(CLAUDE_EMOO_LINK)

    try:
        os.symlink(get_skills_dir(), CLAUDE_EMOO_LINK)
        return True, f"注册成功: {CLAUDE_EMOO_LINK} → {get_skills_dir()}"
    except OSError as e:
        return False, f"创建 symlink 失败: {e}"


def unregister() -> tuple[bool, str]:
    """Remove the Claude Code emoo skill symlink."""
    if os.path.islink(CLAUDE_EMOO_LINK):
        os.unlink(CLAUDE_EMOO_LINK)
        return True, f"已取消注册: {CLAUDE_EMOO_LINK}"
    if os.path.isdir(CLAUDE_EMOO_LINK):
        return False, f"{CLAUDE_EMOO_LINK} 是目录而非 symlink，请手动处理"
    return True, "未找到注册记录，无需操作"


def ensure_skills_dir() -> str:
    """Create ~/.emoo/skills/ if missing.  Returns the path."""
    os.makedirs(get_skills_dir(), exist_ok=True)
    return get_skills_dir()


def copy_example_skills(overwrite: bool = False) -> list[str]:
    """Copy example skill MD files from the package to ~/.emoo/skills/.

    Args:
        overwrite: if True, overwrite existing files.

    Returns:
        list of copied file paths (only newly copied files).
    """
    os.makedirs(get_skills_dir(), exist_ok=True)
    copied = []

    if not os.path.isdir(_EXAMPLES_DIR):
        return copied

    for src in sorted(glob(os.path.join(_EXAMPLES_DIR, "*.md"))):
        dst = os.path.join(get_skills_dir(), os.path.basename(src))
        if os.path.exists(dst) and not overwrite:
            continue
        shutil.copy2(src, dst)
        copied.append(dst)

    return copied
