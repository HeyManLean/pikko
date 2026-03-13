"""
WF2 角色设计: 角色设定 → 角色图
"""

import logging

from agno.db.postgres import PostgresDb
from agno.workflow.step import Step
from agno.workflow.types import OnReject, StepInput, StepOutput
from agno.workflow.workflow import Workflow

from clients.volcengine import VolcengineAPIError, sync_generate_image
from db import db_url, get_session
from models.character import Character
from models.project import Project

logger = logging.getLogger(__name__)


def create_character_setting(step_input: StepInput) -> StepOutput:
    from agents.character_artist import character_artist

    additional = step_input.additional_data or {}
    project_id = additional.get("project_id", "")
    name = additional.get("name", "")
    role = additional.get("role", "")
    personality = additional.get("personality", "")
    appearance = additional.get("appearance", "")
    relationships = additional.get("relationships", "")

    with get_session() as session:
        project = session.get(Project, project_id)
        if not project:
            return StepOutput(content=f"错误：项目 {project_id} 不存在", success=False)

        world_context = ""
        if project.world:
            world_context = f"\n世界观：{project.world.setting or ''}"

        existing_chars = ""
        if project.characters:
            existing_chars = "\n已有角色：" + ", ".join(c.name for c in project.characters)

    prompt = (
        f"请为漫剧「{project.name}」的角色「{name}」生成详细的视觉设定。\n\n"
        f"角色定位：{role}\n性格：{personality}"
    )
    if appearance:
        prompt += f"\n外观参考：{appearance}"
    if relationships:
        prompt += f"\n角色关系：{relationships}"
    prompt += world_context + existing_chars

    response = character_artist.run(prompt)
    content = response.content if response else ""

    with get_session() as session:
        existing = session.query(Character).filter_by(project_id=project_id, name=name).first()
        if existing:
            existing.role = role
            existing.personality = personality
            existing.appearance = content
            existing.relationships = relationships or existing.relationships
            char_id = existing.id
        else:
            char = Character(
                project_id=project_id,
                name=name,
                role=role,
                personality=personality,
                appearance=content,
                relationships=relationships or None,
            )
            session.add(char)
            session.flush()
            char_id = char.id

    return StepOutput(
        content=f"## 角色设定完成：{name}\n\n角色 ID: {char_id}\n\n{content}"
    )


def generate_character_image(step_input: StepInput) -> StepOutput:
    additional = step_input.additional_data or {}
    project_id = additional.get("project_id", "")
    char_name = additional.get("name", "")

    with get_session() as session:
        char = session.query(Character).filter_by(project_id=project_id, name=char_name).first()
        if not char:
            return StepOutput(content=f"错误：角色 {char_name} 不存在", success=False)

        prompt = (
            f"manga character reference sheet, full body, front view, "
            f"character name: {char.name}, role: {char.role or 'unknown'}, "
            f"appearance: {char.appearance or char.personality or 'anime style character'}, "
            f"clean white background, anime style, high quality"
        )
        char.image_prompt = prompt
        char_id = char.id

    image_url: str | None = None
    try:
        image_url = sync_generate_image(prompt)
    except VolcengineAPIError:
        logger.exception("failed to generate character image for %s", char_name)

    if image_url:
        with get_session() as session:
            char = session.get(Character, char_id)
            if char:
                char.image_url = image_url

    status = f"图片已生成：{image_url}" if image_url else "图片生成 API 未配置或调用失败，已保存提示词"
    return StepOutput(
        content=(
            f"## 角色图生成：{char_name}\n\n"
            f"**图片提示词：**\n```\n{prompt}\n```\n\n"
            f"{status}\n\n"
            f"角色设计流程完成！"
        )
    )


wf_character_design = Workflow(
    name="WF2 角色设计",
    description="角色设定 → 角色图",
    db=PostgresDb(db_url=db_url, session_table="wf_character_design_sessions"),
    steps=[
        Step(
            name="create_character_setting",
            executor=create_character_setting,
            description="生成角色视觉设定",
            requires_confirmation=True,
            confirmation_message="角色视觉设定已生成，请确认是否满意？确认后将进入角色图生成。",
            on_reject=OnReject.cancel,
        ),
        Step(
            name="generate_character_image",
            executor=generate_character_image,
            description="生成角色设定图",
            requires_confirmation=True,
            confirmation_message="角色设定图已生成。角色设计流程完成！",
            on_reject=OnReject.cancel,
        ),
    ],
)
