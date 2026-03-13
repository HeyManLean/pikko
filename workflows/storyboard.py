"""
WF4 分镜生成: 生成分镜脚本
"""

from agno.db.postgres import PostgresDb
from agno.workflow.step import Step
from agno.workflow.types import OnReject, StepInput, StepOutput
from agno.workflow.workflow import Workflow

from db import db_url, get_session
from models.episode import Episode
from models.project import Project


def generate_storyboard(step_input: StepInput) -> StepOutput:
    from agents.storyboard_artist import storyboard_artist

    additional = step_input.additional_data or {}
    project_id = additional.get("project_id", "")
    episode_number = additional.get("episode_number", 1)
    scene_number = additional.get("scene_number", 0)

    with get_session() as session:
        episode = (
            session.query(Episode)
            .filter_by(project_id=project_id, number=episode_number)
            .first()
        )
        if not episode:
            return StepOutput(
                content=f"错误：第 {episode_number} 集不存在，请先编写剧本",
                success=False,
            )

        project = session.get(Project, project_id)
        char_context = ""
        if project and project.characters:
            char_context = "\n角色视觉参考：\n" + "\n".join(
                f"- {c.name}: {c.appearance or c.personality or '无描述'}"
                for c in project.characters
            )

        if scene_number > 0:
            prompt = (
                f"请为第 {episode_number} 集的场景 {scene_number} 生成分镜脚本。\n\n"
                f"本集剧本：\n{episode.plot_details or ''}"
            )
        else:
            prompt = (
                f"请为第 {episode_number} 集生成分镜脚本。\n\n"
                f"本集剧本：\n{episode.plot_details or ''}"
            )
        prompt += char_context

        response = storyboard_artist.run(prompt)
        content = response.content if response else ""

        scene_label = f"场景 {scene_number}" if scene_number > 0 else "全部场景"
        return StepOutput(
            content=(
                f"## 第 {episode_number} 集分镜脚本（{scene_label}）\n\n"
                f"{content}\n\n"
                f"分镜生成流程完成！可使用 regenerate_panel 重新生成单个分镜。"
            )
        )


wf_storyboard = Workflow(
    name="WF4 分镜生成",
    description="生成分镜脚本",
    db=PostgresDb(db_url=db_url, session_table="wf_storyboard_sessions"),
    steps=[
        Step(
            name="generate_storyboard",
            executor=generate_storyboard,
            description="生成分镜脚本和画面描述",
            requires_confirmation=True,
            confirmation_message="分镜脚本已生成。分镜生成流程完成！",
            on_reject=OnReject.cancel,
        ),
    ],
)
