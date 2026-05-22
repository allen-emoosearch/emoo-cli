"""EMOO CLI Skill system: adaptive search pipeline.

Skills are a three-stage pipeline:
  1. knowledge-map: scan workspace, generate structured app/doc-group map
  2. intent: analyze natural-language queries against the map, output a search plan
  3. search: execute multi-app search plans and aggregate results
"""

from .knowledge_map import generate_knowledge_map
from .intent import analyze_intent
from .search import execute_search_plan

__all__ = ["generate_knowledge_map", "analyze_intent", "execute_search_plan"]
