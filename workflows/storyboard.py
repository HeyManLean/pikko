"""
WF4 分镜生成: 生成分镜脚本 → 生成分镜图 → 生成视频
"""

import logging

from agno.db.postgres import PostgresDb
from agno.workflow.step import Step
from agno.workflow.types import OnReject, StepInput, StepOutput
from agno.workflow.workflow import Workflow

from clients.volcengine import VolcengineAPIError, sync_generate_image, sync_generate_video
from db import db_url, get_session
from models.episode import Episode, Scene
from models.project import Project
from models.storyboard import StoryboardPanel, Video
from utils.parsers import parse_panels

logger = logging.getLogger(__name__)


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
        episode_id = episode.id
        plot_details = episode.plot_details or ""

        project = session.get(Project, project_id)
        char_context = ""
        if project and project.characters:
            char_context = "\n角色视觉参考：\n" + "\n".join(
                f"- {c.name}: {c.appearance or c.personality or '无描述'}"
                for c in project.characters
            )

        target_scene_id: str | None = None
        if scene_number > 0:
            target_scene = (
                session.query(Scene)
                .filter_by(episode_id=episode_id, number=scene_number)
                .first()
            )
            if target_scene:
                target_scene_id = target_scene.id

    if scene_number > 0:
        prompt = (
            f"请为第 {episode_number} 集的场景 {scene_number} 生成分镜脚本。\n\n"
            f"本集剧本：\n{plot_details}"
        )
    else:
        prompt = (
            f"请为第 {episode_number} 集生成分镜脚本。\n\n"
            f"本集剧本：\n{plot_details}"
        )
    prompt += char_context

    response = storyboard_artist.run(prompt)
    content = response.content if response else ""

    parsed_panels = parse_panels(content)
    logger.info("parsed %d panels from storyboard output", len(parsed_panels))

    with get_session() as session:
        if target_scene_id:
            scene_id = target_scene_id
        else:
            existing_scene = (
                session.query(Scene)
                .filter_by(episode_id=episode_id)
                .order_by(Scene.number)
                .first()
            )
            if existing_scene:
                scene_id = existing_scene.id
            else:
                new_scene = Scene(
                    episode_id=episode_id,
                    number=1,
                    description=f"第 {episode_number} 集默认场景",
                )
                session.add(new_scene)
                session.flush()
                scene_id = new_scene.id

        if target_scene_id:
            session.query(StoryboardPanel).filter_by(scene_id=scene_id).delete()
        elif scene_number == 0:
            scene_ids = [
                s.id for s in session.query(Scene).filter_by(episode_id=episode_id).all()
            ]
            if scene_ids:
                session.query(StoryboardPanel).filter(
                    StoryboardPanel.scene_id.in_(scene_ids)
                ).delete(synchronize_session="fetch")

        for p in parsed_panels:
            panel = StoryboardPanel(
                scene_id=scene_id,
                number=int(p.get("number", 1)),
                description=p.get("description"),
                camera_angle=p.get("camera_angle"),
                dialogue=p.get("dialogue"),
                sfx=p.get("sfx"),
                image_prompt=p.get("image_prompt"),
            )
            session.add(panel)
        session.flush()

        panel_count = len(parsed_panels)

    scene_label = f"场景 {scene_number}" if scene_number > 0 else "全部场景"
    return StepOutput(
        content=(
            f"## 第 {episode_number} 集分镜脚本（{scene_label}）\n\n"
            f"已创建 {panel_count} 个分镜面板记录。\n\n"
            f"{content}\n\n"
            f"确认后将为每个分镜面板生成图片。"
        )
    )


def generate_panel_images(step_input: StepInput) -> StepOutput:
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
            return StepOutput(content=f"错误：第 {episode_number} 集不存在", success=False)

        scene_ids = [
            s.id for s in session.query(Scene).filter_by(episode_id=episode.id).all()
        ]
        panels = (
            session.query(StoryboardPanel)
            .filter(StoryboardPanel.scene_id.in_(scene_ids))
            .order_by(StoryboardPanel.number)
            .all()
            if scene_ids
            else []
        )
        panel_data = [
            {"id": p.id, "number": p.number, "image_prompt": p.image_prompt}
            for p in panels
        ]

    if not panel_data:
        return StepOutput(content="没有找到分镜面板记录，跳过图片生成。")

    success_count = 0
    fail_count = 0

    for pd in panel_data:
        prompt = pd["image_prompt"]
        if not prompt:
            logger.info("panel %s has no image_prompt, skipping", pd["id"])
            continue
        try:
            image_url = sync_generate_image(prompt)
        except VolcengineAPIError:
            logger.exception("failed to generate image for panel %s", pd["id"])
            fail_count += 1
            continue

        if image_url:
            with get_session() as session:
                panel = session.get(StoryboardPanel, pd["id"])
                if panel:
                    panel.image_url = image_url
            success_count += 1
        else:
            fail_count += 1

    status_parts = [f"成功生成 {success_count} 张分镜图"]
    if fail_count:
        status_parts.append(f"，{fail_count} 张生成失败或跳过")

    return StepOutput(
        content=(
            f"## 第 {episode_number} 集分镜图生成\n\n"
            f"{''.join(status_parts)}。\n\n"
            f"确认后将基于分镜图生成视频。"
        )
    )


def generate_episode_video(step_input: StepInput) -> StepOutput:
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
            return StepOutput(content=f"错误：第 {episode_number} 集不存在", success=False)
        episode_id = episode.id
        episode_title = episode.title or f"第 {episode_number} 集"
        episode_synopsis = episode.synopsis or ""

        scene_ids = [
            s.id for s in session.query(Scene).filter_by(episode_id=episode_id).all()
        ]
        panels = (
            session.query(StoryboardPanel)
            .filter(StoryboardPanel.scene_id.in_(scene_ids))
            .order_by(StoryboardPanel.number)
            .all()
            if scene_ids
            else []
        )
        first_panel_image = None
        for p in panels:
            if p.image_url:
                first_panel_image = p.image_url
                break

    video_prompt = (
        f"anime manga style short video, {episode_title}, "
        f"{episode_synopsis[:200]}, "
        f"dynamic camera movement, cinematic lighting"
    )

    references = []
    if first_panel_image:
        references.append(("first_frame", first_panel_image))

    video_result: tuple[str, str] | None = None
    try:
        video_result = sync_generate_video(
            video_prompt, references=references, ratio="9:16", duration_sec=5,
        )
    except VolcengineAPIError:
        logger.exception("failed to generate video for episode %d", episode_number)

    if video_result:
        task_id, video_url = video_result
        with get_session() as session:
            existing_video = session.query(Video).filter_by(episode_id=episode_id).first()
            if existing_video:
                existing_video.video_url = video_url
                existing_video.status = "completed"
            else:
                session.add(Video(
                    episode_id=episode_id,
                    video_url=video_url,
                    status="completed",
                ))

        return StepOutput(
            content=(
                f"## 第 {episode_number} 集视频生成\n\n"
                f"视频已生成！\n"
                f"- Task ID: {task_id}\n"
                f"- 视频 URL: {video_url}\n\n"
                f"分镜生成流程全部完成！"
            )
        )

    return StepOutput(
        content=(
            f"## 第 {episode_number} 集视频生成\n\n"
            f"视频生成 API 未配置或调用失败，已跳过。\n"
            f"提示词已保存：{video_prompt}\n\n"
            f"分镜生成流程全部完成！"
        )
    )


wf_storyboard = Workflow(
    name="WF4 分镜生成",
    description="生成分镜脚本 → 生成分镜图 → 生成视频",
    db=PostgresDb(db_url=db_url, session_table="wf_storyboard_sessions"),
    steps=[
        Step(
            name="generate_storyboard",
            executor=generate_storyboard,
            description="生成分镜脚本和画面描述",
            requires_confirmation=True,
            confirmation_message="分镜脚本已生成，请确认是否满意？确认后将为每个分镜生成图片。",
            on_reject=OnReject.cancel,
        ),
        Step(
            name="generate_panel_images",
            executor=generate_panel_images,
            description="为每个分镜面板生成图片",
            requires_confirmation=True,
            confirmation_message="分镜图已生成，请确认是否满意？确认后将生成视频。",
            on_reject=OnReject.cancel,
        ),
        Step(
            name="generate_episode_video",
            executor=generate_episode_video,
            description="基于分镜图生成视频",
            requires_confirmation=True,
            confirmation_message="视频已生成。分镜生成流程全部完成！",
            on_reject=OnReject.cancel,
        ),
    ],
)
