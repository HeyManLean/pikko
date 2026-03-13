"""
WF1 世界构建: 创建世界观 → 设计角色网络 → 创建剧情大纲
"""

import logging

from agno.db.postgres import PostgresDb
from agno.workflow.step import Step
from agno.workflow.types import OnReject, StepInput, StepOutput
from agno.workflow.workflow import Workflow

from db import db_url, get_session
from models.character import Character
from models.project import Project
from models.world import PlotOutline, World
from utils.parsers import parse_characters, parse_plot_outline

logger = logging.getLogger(__name__)


def _get_project_context(session, project_id: str) -> dict:
    project = session.get(Project, project_id)
    if not project:
        return {}
    ctx: dict = {
        "project_name": project.name,
        "description": project.description,
        "genre": project.genre,
    }
    if project.world:
        ctx["world"] = {
            "setting": project.world.setting,
            "rules": project.world.rules,
            "atmosphere": project.world.atmosphere,
            "background_story": project.world.background_story,
        }
    if project.characters:
        ctx["characters"] = [
            {"name": c.name, "role": c.role, "personality": c.personality, "appearance": c.appearance}
            for c in project.characters
        ]
    if project.plot_outline:
        ctx["plot_outline"] = {
            "synopsis": project.plot_outline.synopsis,
            "themes": project.plot_outline.themes,
            "arc_structure": project.plot_outline.arc_structure,
        }
    return ctx


def build_world(step_input: StepInput) -> StepOutput:
    from agents.world_builder import world_builder

    additional = step_input.additional_data or {}
    project_id = additional.get("project_id", "")
    extra_req = additional.get("additional_requirements", "")

    with get_session() as session:
        project = session.get(Project, project_id)
        if not project:
            return StepOutput(content=f"错误：项目 {project_id} 不存在", success=False)
        project_name = project.name
        project_desc = project.description
        project_genre = project.genre

    prompt = (
        f"请为漫剧「{project_name}」构建世界观设定。\n\n"
        f"项目描述：{project_desc}\n题材：{project_genre or '未指定'}"
    )
    if extra_req:
        prompt += f"\n\n额外要求：{extra_req}"

    response = world_builder.run(prompt)
    content = response.content if response else ""

    with get_session() as session:
        existing = session.query(World).filter_by(project_id=project_id).first()
        if existing:
            existing.setting = content
        else:
            session.add(World(project_id=project_id, setting=content))

    return StepOutput(content=content)


def design_character_network(step_input: StepInput) -> StepOutput:
    from agents.character_architect import character_architect

    additional = step_input.additional_data or {}
    project_id = additional.get("project_id", "")
    extra_req = additional.get("additional_requirements", "")

    with get_session() as session:
        ctx = _get_project_context(session, project_id)
        if not ctx:
            return StepOutput(content=f"错误：项目 {project_id} 不存在", success=False)

    prompt = (
        f"请为漫剧「{ctx['project_name']}」设计角色网络。\n\n"
        f"项目描述：{ctx['description']}\n题材：{ctx.get('genre', '未指定')}"
    )
    if ctx.get("world"):
        prompt += f"\n\n已有世界观设定：\n{ctx['world'].get('setting', '')}"
    if extra_req:
        prompt += f"\n\n额外要求：{extra_req}"

    response = character_architect.run(prompt)
    content = response.content if response else ""

    parsed_chars = parse_characters(content)
    logger.info("parsed %d characters from character_architect output", len(parsed_chars))

    with get_session() as session:
        for c in parsed_chars:
            name = c.get("name", "")
            if not name:
                continue
            existing = session.query(Character).filter_by(
                project_id=project_id, name=name
            ).first()
            if existing:
                if c.get("role"):
                    existing.role = c["role"]
                if c.get("personality"):
                    existing.personality = c["personality"]
                if c.get("appearance"):
                    existing.appearance = c["appearance"]
                if c.get("relationships"):
                    existing.relationships = c["relationships"]
            else:
                session.add(Character(
                    project_id=project_id,
                    name=name,
                    role=c.get("role"),
                    personality=c.get("personality"),
                    appearance=c.get("appearance"),
                    relationships=c.get("relationships"),
                ))

    char_count = len(parsed_chars)
    return StepOutput(
        content=(
            f"{content}\n\n"
            f"---\n已创建/更新 {char_count} 个角色记录。"
        )
    )


def create_plot_outline(step_input: StepInput) -> StepOutput:
    from agents.plot_designer import plot_designer

    additional = step_input.additional_data or {}
    project_id = additional.get("project_id", "")
    extra_req = additional.get("additional_requirements", "")

    with get_session() as session:
        ctx = _get_project_context(session, project_id)
        if not ctx:
            return StepOutput(content=f"错误：项目 {project_id} 不存在", success=False)

    prompt = (
        f"请为漫剧「{ctx['project_name']}」设计剧情大纲。\n\n"
        f"项目描述：{ctx['description']}\n题材：{ctx.get('genre', '未指定')}"
    )
    if ctx.get("world"):
        prompt += f"\n\n世界观设定：\n{ctx['world'].get('setting', '')}"
    if ctx.get("characters"):
        chars_text = "\n".join(
            f"- {c['name']}（{c.get('role', '未定义')}）：{c.get('personality', '')}"
            for c in ctx["characters"]
        )
        prompt += f"\n\n已有角色：\n{chars_text}"
    if extra_req:
        prompt += f"\n\n额外要求：{extra_req}"

    response = plot_designer.run(prompt)
    content = response.content if response else ""

    parsed = parse_plot_outline(content)

    with get_session() as session:
        existing = session.query(PlotOutline).filter_by(project_id=project_id).first()
        if existing:
            existing.synopsis = parsed.get("synopsis") or content
            existing.themes = parsed.get("themes")
            existing.arc_structure = parsed.get("arc_structure")
            if parsed.get("total_episodes") is not None:
                existing.total_episodes = parsed["total_episodes"]
        else:
            session.add(PlotOutline(
                project_id=project_id,
                synopsis=parsed.get("synopsis") or content,
                themes=parsed.get("themes"),
                arc_structure=parsed.get("arc_structure"),
                total_episodes=parsed.get("total_episodes"),
            ))

    return StepOutput(content=content)


wf_world_building = Workflow(
    name="WF1 世界构建",
    description="创建世界观 → 设计角色网络 → 创建剧情大纲",
    db=PostgresDb(db_url=db_url, session_table="wf_world_building_sessions"),
    steps=[
        Step(
            name="create_world",
            executor=build_world,
            description="构建漫剧世界观设定",
            requires_confirmation=True,
            confirmation_message="世界观设定已生成，请确认是否满意？确认后将进入角色网络设计。",
            on_reject=OnReject.cancel,
        ),
        Step(
            name="design_character_network",
            executor=design_character_network,
            description="设计角色网络和关系图谱",
            requires_confirmation=True,
            confirmation_message="角色网络已设计完成，请确认是否满意？确认后将进入剧情大纲创建。",
            on_reject=OnReject.cancel,
        ),
        Step(
            name="create_plot_outline",
            executor=create_plot_outline,
            description="创建剧情大纲和故事弧线",
            requires_confirmation=True,
            confirmation_message="剧情大纲已创建。世界构建流程全部完成！",
            on_reject=OnReject.cancel,
        ),
    ],
)
