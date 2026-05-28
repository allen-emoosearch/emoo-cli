"""Claude Code skill registry: symlink ~/.emoo/skills/ → ~/.claude/skills/emoo/."""

import os
import shutil
from glob import glob
from pathlib import Path

EMOO_SKILLS_DIR = os.path.expanduser("~/.emoo/skills")
CLAUDE_SKILLS_DIR = os.path.expanduser("~/.claude/skills")
CLAUDE_EMOO_LINK = os.path.join(CLAUDE_SKILLS_DIR, "emoo")

# Package examples directory (relative to this file)
_EXAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "examples")


def is_registered() -> bool:
    """Check if emoo skills are already registered in Claude Code."""
    if os.path.islink(CLAUDE_EMOO_LINK):
        target = os.readlink(CLAUDE_EMOO_LINK)
        return os.path.samefile(target, EMOO_SKILLS_DIR) if os.path.exists(target) else False
    if os.path.isdir(CLAUDE_EMOO_LINK):
        return os.path.samefile(CLAUDE_EMOO_LINK, EMOO_SKILLS_DIR)
    return False


def register_symlink() -> tuple[bool, str]:
    """Create symlink ~/.claude/skills/emoo → ~/.emoo/skills/.

    Returns (success, message).
    """
    os.makedirs(EMOO_SKILLS_DIR, exist_ok=True)
    os.makedirs(CLAUDE_SKILLS_DIR, exist_ok=True)

    if os.path.islink(CLAUDE_EMOO_LINK):
        current = os.readlink(CLAUDE_EMOO_LINK)
        if os.path.exists(current) and os.path.samefile(current, EMOO_SKILLS_DIR):
            return True, f"已注册: {CLAUDE_EMOO_LINK} → {EMOO_SKILLS_DIR}"
        os.unlink(CLAUDE_EMOO_LINK)
    elif os.path.isdir(CLAUDE_EMOO_LINK):
        if os.path.samefile(CLAUDE_EMOO_LINK, EMOO_SKILLS_DIR):
            return True, f"已注册: {CLAUDE_EMOO_LINK} (目录模式)"
        return False, f"{CLAUDE_EMOO_LINK} 已存在但不是指向 {EMOO_SKILLS_DIR}，请手动处理"
    elif os.path.exists(CLAUDE_EMOO_LINK):
        os.unlink(CLAUDE_EMOO_LINK)

    try:
        os.symlink(EMOO_SKILLS_DIR, CLAUDE_EMOO_LINK)
        return True, f"注册成功: {CLAUDE_EMOO_LINK} → {EMOO_SKILLS_DIR}"
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
    os.makedirs(EMOO_SKILLS_DIR, exist_ok=True)
    return EMOO_SKILLS_DIR


def copy_example_skills(overwrite: bool = False) -> list[str]:
    """Copy example skill MD files from the package to ~/.emoo/skills/.

    Args:
        overwrite: if True, overwrite existing files.

    Returns:
        list of copied file paths (only newly copied files).
    """
    os.makedirs(EMOO_SKILLS_DIR, exist_ok=True)
    copied = []

    if not os.path.isdir(_EXAMPLES_DIR):
        return copied

    for src in sorted(glob(os.path.join(_EXAMPLES_DIR, "*.md"))):
        dst = os.path.join(EMOO_SKILLS_DIR, os.path.basename(src))
        if os.path.exists(dst) and not overwrite:
            continue
        shutil.copy2(src, dst)
        copied.append(dst)

    return copied
