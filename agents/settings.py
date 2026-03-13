"""
Shared agent settings. Import from here — never recreate.
"""

from pathlib import Path

from agno.models.openai import OpenAIChat

from db import create_knowledge

# -- Model configuration (change here to affect all agents) --
default_model = OpenAIChat(id="gpt-4o")
smart_model = OpenAIChat(id="gpt-4o")

team_knowledge = create_knowledge("Team Knowledge", "team_knowledge")
team_learnings = create_knowledge("Team Learnings", "team_learnings")

OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"
