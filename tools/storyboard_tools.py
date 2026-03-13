"""
Storyboard CRUD tools for the orchestrator.
"""

import json
import logging

from agno.tools import tool

from clients.volcengine import VolcengineAPIError, sync_generate_image
from db import get_session
from models.episode import Episode
from models.storyboard import StoryboardPanel

logger = logging.getLogger(__name__)


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
        old_description = panel.description or ""
        old_camera = panel.camera_angle or ""
        old_dialogue = panel.dialogue or ""

    prompt = (
        f"请重新生成这个分镜面板。\n\n"
        f"原始描述：{old_description}\n"
        f"镜头：{old_camera}\n"
        f"对白：{old_dialogue}"
    )
    if additional_requirements:
        prompt += f"\n\n修改要求：{additional_requirements}"

    response = storyboard_artist.run(prompt)
    content = response.content if response else ""

    image_url: str | None = None
    image_prompt = (
        f"manga panel, {content[:300]}, anime style, high quality, detailed"
    )
    try:
        image_url = sync_generate_image(image_prompt)
    except VolcengineAPIError:
        logger.exception("failed to regenerate panel image for %s", panel_id)

    with get_session() as session:
        panel = session.get(StoryboardPanel, panel_id)
        if panel:
            panel.description = content
            panel.image_prompt = image_prompt
            if image_url:
                panel.image_url = image_url

    return json.dumps({
        "status": "success",
        "panel_id": panel_id,
        "result": content,
        "image_url": image_url,
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
