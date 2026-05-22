"""MD skill loader: parse YAML frontmatter from Markdown skill files.

Skill files live in ~/.emoo/skills/*.md and use YAML frontmatter + markdown body.

Frontmatter schema:
  name: skill-name          # required, unique identifier
  description: ...          # required, one-line summary
  type: scenario|dimension  # required
  category: ...             # optional, grouping label
  tags: [...]               # optional
  emoo:                     # required, CLI execution config
    search:
      keyword: "..."        # required, {param} template
      app: "..."            # optional, auto-matched by name
      doc_group: "..."      # optional, auto-matched by name
      filters: [...]        # optional, static filter conditions
      page_size: 200        # optional, default 200
    params:                 # optional
      param_name:
        description: "..."
        required: true|false
        default: "..."
        example: "..."
        choices: [...]      # optional
        map_to: time_range  # optional
    csv_export: false       # optional, default false
"""

import os
import re
from glob import glob
from typing import Any, Optional

import yaml


SKILLS_DIR = os.path.expanduser("~/.emoo/skills")

# Regex: split frontmatter (between --- delimiters) from markdown body
_FM_PATTERN = re.compile(r'^---\s*\n(.*?)\n---\s*\n?(.*)', re.DOTALL)


class SkillDef:
    """Parsed skill definition from an MD file."""

    def __init__(self, raw: dict, body: str, filepath: str):
        self.name: str = raw.get("name", "")
        self.description: str = raw.get("description", "")
        self.type: str = raw.get("type", "scenario")
        self.category: str = raw.get("category", "未分类")
        self.tags: list[str] = raw.get("tags", [])
        self.body: str = body.strip()
        self.filepath: str = filepath

        emoo_cfg = raw.get("emoo", {})
        search_cfg = emoo_cfg.get("search", {})
        self.keyword: str = search_cfg.get("keyword", "")
        self.app_name: str = search_cfg.get("app", "")
        self.doc_group_name: str = search_cfg.get("doc_group", "")
        self.filters: list = search_cfg.get("filters", [])
        self.page_size: int = search_cfg.get("page_size", 200)
        self.csv_export: bool = emoo_cfg.get("csv_export", False)

        params_raw = emoo_cfg.get("params", {}) or {}
        self.params: dict[str, dict] = {}
        for pname, pdef in params_raw.items():
            self.params[pname] = {
                "description": pdef.get("description", ""),
                "required": pdef.get("required", False),
                "default": pdef.get("default"),
                "example": pdef.get("example", ""),
                "choices": pdef.get("choices"),
                "map_to": pdef.get("map_to"),
            }

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "category": self.category,
            "tags": self.tags,
            "file": self.filepath,
            "keyword": self.keyword,
            "app": self.app_name,
            "doc_group": self.doc_group_name,
            "params": [{"name": k, **v} for k, v in self.params.items()],
            "csv_export": self.csv_export,
        }


def parse_skill_file(filepath: str) -> Optional[SkillDef]:
    """Parse a single skill MD file.  Returns None if no valid frontmatter."""
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    m = _FM_PATTERN.match(content)
    if not m:
        return None

    frontmatter = m.group(1)
    body = m.group(2)

    try:
        raw = yaml.safe_load(frontmatter)
    except yaml.YAMLError:
        return None

    if not isinstance(raw, dict):
        return None

    if not raw.get("name") or not raw.get("emoo"):
        return None

    return SkillDef(raw, body, filepath)


def load_all_skills(skills_dir: str = SKILLS_DIR) -> list[SkillDef]:
    """Load all valid skill MD files from the skills directory."""
    if not os.path.isdir(skills_dir):
        return []

    skills = []
    for filepath in sorted(glob(os.path.join(skills_dir, "*.md"))):
        sd = parse_skill_file(filepath)
        if sd:
            skills.append(sd)

    return skills


def find_skill(name: str, skills_dir: str = SKILLS_DIR) -> Optional[SkillDef]:
    """Find a skill by name (matches filename stem or frontmatter name)."""
    # Try exact filename match first
    filepath = os.path.join(skills_dir, f"{name}.md")
    if os.path.isfile(filepath):
        return parse_skill_file(filepath)

    # Fall back to scanning all files for matching frontmatter name
    for sd in load_all_skills(skills_dir):
        if sd.name == name:
            return sd

    return None


def validate_params(skill: SkillDef, user_params: dict[str, str]) -> list[str]:
    """Validate user-provided params against skill definition.  Returns list of errors."""
    errors = []

    for pname, pdef in skill.params.items():
        if pdef["required"] and pname not in user_params:
            if pdef.get("default") is None:
                errors.append(f"缺少必填参数: --{pname} ({pdef['description']})")

    for pname in user_params:
        if pname not in skill.params:
            errors.append(f"未知参数: --{pname} (skill 未定义此参数)")

    return errors
