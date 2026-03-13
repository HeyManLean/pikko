"""
Storyboard CRUD tools for the orchestrator.
"""

import json

from agno.tools import tool

from db import get_session
from models.episode import Episode
from models.storyboard import StoryboardPanel


@tool(stop_after_tool_call=True)
def regenerate_panel(panel_id: str, additional_requirements: str = "") -> str:
    """重新生成指定的分镜面板。

    Args:
        panel_id: 分镜面板 ID
        additional_requirements: 对重新生成的额外要求
    """
    from agents.storyboard_artist import storyboard_artist

    with get_session() as session:
        panel = session.get(StoryboardPanel, panel_id)
        if not panel:
            return json.dumps({"error": f"分镜面板 {panel_id} 不存在"}, ensure_ascii=False)

        prompt = (
            f"请重新生成这个分镜面板。\n\n"
            f"原始描述：{panel.description or ''}\n"
            f"镜头：{panel.camera_angle or ''}\n"
            f"对白：{panel.dialogue or ''}"
        )
        if additional_requirements:
            prompt += f"\n\n修改要求：{additional_requirements}"

        response = storyboard_artist.run(prompt)
        content = response.content if response else ""

        panel.description = content
        # TODO: regenerate image via image generation API
        panel.image_url = None

        return json.dumps({
            "status": "success",
            "panel_id": panel.id,
            "result": content,
        }, ensure_ascii=False)


@tool
def list_storyboard_panels(episode_id: str) -> str:
    """列出某集的所有分镜面板。

    Args:
        episode_id: 剧集 ID
    """
    with get_session() as session:
        episode = session.get(Episode, episode_id)
        if not episode:
            return json.dumps({"error": f"剧集 {episode_id} 不存在"}, ensure_ascii=False)

        panels = []
        for scene in episode.scenes:
            for panel in scene.panels:
                panels.append({
                    "id": panel.id,
                    "scene_number": scene.number,
                    "panel_number": panel.number,
                    "description": panel.description,
                    "camera_angle": panel.camera_angle,
                    "has_image": bool(panel.image_url),
                })

        return json.dumps({
            "episode_id": episode_id,
            "episode_number": episode.number,
            "total_panels": len(panels),
            "panels": panels,
        }, ensure_ascii=False)
