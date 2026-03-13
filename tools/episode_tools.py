"""
Episode CRUD tools for the orchestrator.
"""

import json

from agno.tools import tool

from db import get_session
from models.episode import Episode


@tool
def update_episode(episode_id: str, field: str, value: str) -> str:
    """更新剧集的某个字段。

    Args:
        episode_id: 剧集 ID
        field: 要更新的字段名（title/synopsis/plot_details）
        value: 新的值
    """
    allowed_fields = {"title", "synopsis", "plot_details"}
    if field not in allowed_fields:
        return json.dumps({"error": f"不支持的字段: {field}，可选: {allowed_fields}"}, ensure_ascii=False)

    with get_session() as session:
        episode = session.get(Episode, episode_id)
        if not episode:
            return json.dumps({"error": f"剧集 {episode_id} 不存在"}, ensure_ascii=False)

        setattr(episode, field, value)
        return json.dumps({
            "status": "success",
            "episode_id": episode.id,
            "updated_field": field,
        }, ensure_ascii=False)


@tool
def list_episodes(project_id: str) -> str:
    """列出项目下的所有剧集。

    Args:
        project_id: 项目 ID
    """
    with get_session() as session:
        episodes = session.query(Episode).filter_by(project_id=project_id).order_by(Episode.number).all()
        result = [
            {
                "id": e.id,
                "number": e.number,
                "title": e.title,
                "synopsis": e.synopsis,
                "scene_count": len(e.scenes),
            }
            for e in episodes
        ]
        return json.dumps(result, ensure_ascii=False)


@tool
def get_episode_detail(episode_id: str) -> str:
    """获取单集的详细信息，包含场景和分镜。

    Args:
        episode_id: 剧集 ID
    """
    with get_session() as session:
        episode = session.get(Episode, episode_id)
        if not episode:
            return json.dumps({"error": f"剧集 {episode_id} 不存在"}, ensure_ascii=False)

        scenes = []
        for s in episode.scenes:
            scene_data: dict = {
                "id": s.id,
                "number": s.number,
                "description": s.description,
                "location": s.location,
                "characters_involved": s.characters_involved,
                "panel_count": len(s.panels),
            }
            scenes.append(scene_data)

        return json.dumps({
            "id": episode.id,
            "number": episode.number,
            "title": episode.title,
            "synopsis": episode.synopsis,
            "plot_details": episode.plot_details,
            "scenes": scenes,
        }, ensure_ascii=False)
