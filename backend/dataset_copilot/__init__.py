"""Dataset Copilot: LLM-driven generator that turns a business briefing markdown
into a complete bookshelf payload (LLD/DDL/data_dictionary/golden_sql/agent_prompts/...).
"""

from .payload_generator import DatasetCopilot, CopilotError

__all__ = ["DatasetCopilot", "CopilotError"]
