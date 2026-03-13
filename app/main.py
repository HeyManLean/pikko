"""
Pikko - 漫剧制作 Agent 系统
----------------------------

Run:
  python -m app.main
"""

import os

from agno.os import AgentOS

from agents import orchestrator
from db import get_postgres_db, init_db

init_db()

agent_os = AgentOS(
    name="Pikko 漫剧制作助手",
    tracing=True,
    scheduler=True,
    db=get_postgres_db(),
    agents=[orchestrator],
)

app = agent_os.get_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RUNTIME_ENV", "") == "dev"
    agent_os.serve(app="app.main:app", port=port, reload=reload)
