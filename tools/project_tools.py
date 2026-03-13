"""
Project CRUD tools for the orchestrator.
"""

import json

from agno.tools import tool

from db import get_session
from models.project import Project


@tool(stop_after_tool_call=True)
def create_project(name: str, description: str, genre: str = "", target_audience: str = "") -> str:
    """创建一个新的漫剧项目。在开始任何创作之前必须先创建项目。

    Args:
        name: 项目名称
        description: 项目描述/核心创意
        genre: 题材类型（如：都市奇幻、校园恋爱、科幻冒险）
        target_audience: 目标受众（如：12-18岁青少年）
    """
    with get_session() as session:
        project = Project(
            name=name,
            description=description,
            genre=genre or None,
            target_audience=target_audience or None,
        )
        session.add(project)
        session.flush()
        return json.dumps({
            "status": "success",
            "project_id": project.id,
            "name": project.name,
            "description": project.description,
            "genre": project.genre,
            "target_audience": project.target_audience,
        }, ensure_ascii=False)


@tool
def list_projects() -> str:
    """列出所有漫剧项目。"""
    with get_session() as session:
        projects = session.query(Project).order_by(Project.created_at.desc()).all()
        result = []
        for p in projects:
            result.append({
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "genre": p.genre,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            })
        return json.dumps(result, ensure_ascii=False)


@tool
def get_project_summary(project_id: str) -> str:
    """获取项目的完整概况，包含世界观、角色、剧情大纲、剧集等信息。

    Args:
        project_id: 项目 ID
    """
    with get_session() as session:
        project = session.get(Project, project_id)
        if not project:
            return json.dumps({"error": f"项目 {project_id} 不存在"}, ensure_ascii=False)

        summary: dict = {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "genre": project.genre,
            "target_audience": project.target_audience,
        }

        if project.world:
            summary["world"] = {
                "setting": project.world.setting,
                "rules": project.world.rules,
                "atmosphere": project.world.atmosphere,
                "background_story": project.world.background_story,
            }

        if project.characters:
            summary["characters"] = [
                {"id": c.id, "name": c.name, "role": c.role, "personality": c.personality}
                for c in project.characters
            ]

        if project.plot_outline:
            summary["plot_outline"] = {
                "synopsis": project.plot_outline.synopsis,
                "themes": project.plot_outline.themes,
                "total_episodes": project.plot_outline.total_episodes,
            }

        if project.episodes:
            summary["episodes"] = [
                {"id": e.id, "number": e.number, "title": e.title, "synopsis": e.synopsis}
                for e in project.episodes
            ]

        return json.dumps(summary, ensure_ascii=False)
