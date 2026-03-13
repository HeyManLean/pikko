"""
WF3 单集制作: 编写单集剧本 → 提取场景元素
"""

from agno.db.postgres import PostgresDb
from agno.workflow.step import Step
from agno.workflow.types import OnReject, StepInput, StepOutput
from agno.workflow.workflow import Workflow

from db import db_url, get_session
from models.episode import Episode
from models.project import Project


def _build_episode_context(session, project_id: str) -> str:
    project = session.get(Project, project_id)
    if not project:
        return ""

    parts = [f"漫剧名称：{project.name}", f"项目描述：{project.description}"]

    if project.genre:
        parts.append(f"题材：{project.genre}")
    if project.world:
        parts.append(f"世界观设定：\n{project.world.setting or ''}")
    if project.characters:
        chars = "\n".join(
            f"- {c.name}（{c.role or '未定义'}）：{c.personality or ''}"
            for c in project.characters
        )
        parts.append(f"角色列表：\n{chars}")
    if project.plot_outline:
        parts.append(f"剧情大纲：\n{project.plot_outline.synopsis or ''}")

    existing_episodes = (
        session.query(Episode).filter_by(project_id=project_id).order_by(Episode.number).all()
    )
    if existing_episodes:
        eps = "\n".join(
            f"- 第{e.number}集「{e.title or '未命名'}」：{e.synopsis or ''}"
            for e in existing_episodes
        )
        parts.append(f"已完成剧集：\n{eps}")

    return "\n\n".join(parts)


def write_episode_script(step_input: StepInput) -> StepOutput:
    from agents.episode_writer import episode_writer

    additional = step_input.additional_data or {}
    project_id = additional.get("project_id", "")
    episode_number = additional.get("episode_number", 1)
    extra_req = additional.get("additional_requirements", "")

    with get_session() as session:
        context = _build_episode_context(session, project_id)
        if not context:
            return StepOutput(content=f"错误：项目 {project_id} 不存在", success=False)

        prompt = f"请编写第 {episode_number} 集的详细剧本。\n\n{context}"
        if extra_req:
            prompt += f"\n\n额外要求：{extra_req}"

        response = episode_writer.run(prompt)
        content = response.content if response else ""

        existing = (
            session.query(Episode)
            .filter_by(project_id=project_id, number=episode_number)
            .first()
        )
        if existing:
            existing.plot_details = content
            existing.synopsis = content[:200] if content else None
            episode_id = existing.id
        else:
            ep = Episode(
                project_id=project_id,
                number=episode_number,
                plot_details=content,
                synopsis=content[:200] if content else None,
            )
            session.add(ep)
            session.flush()
            episode_id = ep.id

        return StepOutput(
            content=f"## 第 {episode_number} 集剧本\n\n剧集 ID: {episode_id}\n\n{content}"
        )


def extract_scene_elements(step_input: StepInput) -> StepOutput:
    from agents.scene_designer import scene_designer

    additional = step_input.additional_data or {}
    project_id = additional.get("project_id", "")
    episode_number = additional.get("episode_number", 1)

    with get_session() as session:
        episode = (
            session.query(Episode)
            .filter_by(project_id=project_id, number=episode_number)
            .first()
        )
        if not episode:
            return StepOutput(
                content=f"错误：第 {episode_number} 集不存在", success=False
            )

        context = _build_episode_context(session, project_id)

        prompt = (
            f"请从第 {episode_number} 集的剧本中提取并设计所有视觉元素。\n\n"
            f"项目背景：\n{context}\n\n"
            f"本集剧本：\n{episode.plot_details or ''}"
        )

        response = scene_designer.run(prompt)
        content = response.content if response else ""

        return StepOutput(
            content=f"## 第 {episode_number} 集视觉元素\n\n{content}\n\n单集制作流程完成！"
        )


wf_episode_production = Workflow(
    name="WF3 单集制作",
    description="编写单集剧本 → 提取场景元素",
    db=PostgresDb(db_url=db_url, session_table="wf_episode_production_sessions"),
    steps=[
        Step(
            name="write_episode_script",
            executor=write_episode_script,
            description="编写单集详细剧本",
            requires_confirmation=True,
            confirmation_message="单集剧本已编写完成，请确认是否满意？确认后将进入场景元素提取。",
            on_reject=OnReject.cancel,
        ),
        Step(
            name="extract_scene_elements",
            executor=extract_scene_elements,
            description="从剧本中提取场景、道具和新角色",
            requires_confirmation=True,
            confirmation_message="场景元素已提取完成。单集制作流程结束！",
            on_reject=OnReject.cancel,
        ),
    ],
)
