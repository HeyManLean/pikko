"""
Workflow runner tools — orchestrator 通过这些工具启动、确认、拒绝、查询工作流。
"""

import json
from typing import Any

from agno.tools import tool

from workflows import (
    wf_character_design,
    wf_episode_production,
    wf_storyboard,
    wf_world_building,
)

WORKFLOWS = {
    "wf1_world_building": wf_world_building,
    "wf2_character_design": wf_character_design,
    "wf3_episode": wf_episode_production,
    "wf4_storyboard": wf_storyboard,
}

WORKFLOW_LABELS = {
    "wf1_world_building": "WF1 世界构建（世界观→角色网络→剧情大纲）",
    "wf2_character_design": "WF2 角色设计（角色设定→角色图）",
    "wf3_episode": "WF3 单集制作（单集剧本→场景元素提取）",
    "wf4_storyboard": "WF4 分镜生成",
}


def _format_run_output(run_output: Any, workflow_name: str) -> dict:
    """Extract useful information from a WorkflowRunOutput."""
    result: dict = {
        "workflow": workflow_name,
        "workflow_label": WORKFLOW_LABELS.get(workflow_name, workflow_name),
        "run_id": run_output.run_id,
        "session_id": run_output.session_id,
        "status": run_output.status.value if hasattr(run_output.status, "value") else str(run_output.status),
    }

    if run_output.is_paused:
        result["is_paused"] = True
        result["paused_step"] = run_output.paused_step_name
        confirmations = run_output.steps_requiring_confirmation
        if confirmations:
            result["confirmation_message"] = confirmations[0].confirmation_message

    if run_output.content:
        content = run_output.content
        if hasattr(content, "model_dump"):
            content = str(content)
        result["content"] = str(content) if content else None

    if run_output.step_results:
        last_step = run_output.step_results[-1]
        if hasattr(last_step, "content") and last_step.content:
            result["last_step_content"] = str(last_step.content)
        if hasattr(last_step, "step_name"):
            result["last_step_name"] = last_step.step_name

    return result


@tool(stop_after_tool_call=True)
def start_workflow(
    workflow_name: str,
    project_id: str,
    additional_requirements: str = "",
    name: str = "",
    role: str = "",
    personality: str = "",
    appearance: str = "",
    relationships: str = "",
    episode_number: int = 0,
    scene_number: int = 0,
) -> str:
    """启动一个工作流。

    Args:
        workflow_name: 工作流名称。可选值：wf1_world_building（世界构建）、wf2_character_design（角色设计）、wf3_episode（单集制作）、wf4_storyboard（分镜生成）
        project_id: 项目 ID
        additional_requirements: 额外要求（可选）
        name: 角色名称（WF2 角色设计时必填）
        role: 角色定位（WF2 角色设计时必填）
        personality: 角色性格（WF2 角色设计时必填）
        appearance: 角色外观（可选）
        relationships: 角色关系（可选）
        episode_number: 集数编号（WF3/WF4 时必填）
        scene_number: 场景编号（WF4 时可选，0表示全部）
    """
    wf = WORKFLOWS.get(workflow_name)
    if not wf:
        return json.dumps(
            {"error": f"未知工作流: {workflow_name}，可选: {list(WORKFLOWS.keys())}"},
            ensure_ascii=False,
        )

    additional_data: dict[str, Any] = {
        "project_id": project_id,
        "additional_requirements": additional_requirements,
    }

    if workflow_name == "wf2_character_design":
        additional_data.update(
            name=name, role=role, personality=personality,
            appearance=appearance, relationships=relationships,
        )
    elif workflow_name in ("wf3_episode", "wf4_storyboard"):
        additional_data["episode_number"] = episode_number
        if workflow_name == "wf4_storyboard":
            additional_data["scene_number"] = scene_number

    run_output = wf.run(
        input=f"执行 {WORKFLOW_LABELS.get(workflow_name, workflow_name)}",
        additional_data=additional_data,
    )

    return json.dumps(_format_run_output(run_output, workflow_name), ensure_ascii=False)


@tool(stop_after_tool_call=True)
def confirm_workflow_step(workflow_name: str, session_id: str) -> str:
    """确认当前暂停的工作流步骤，继续执行下一步。

    Args:
        workflow_name: 工作流名称
        session_id: 工作流 session ID（从 start_workflow 或上次 confirm 的返回值中获取）
    """
    wf = WORKFLOWS.get(workflow_name)
    if not wf:
        return json.dumps({"error": f"未知工作流: {workflow_name}"}, ensure_ascii=False)

    session = wf.get_session(session_id=session_id)
    if not session or not session.runs:
        return json.dumps({"error": f"找不到 session: {session_id}"}, ensure_ascii=False)

    last_run = session.runs[-1]
    run_output = wf.get_last_run_output(session_id=session_id)
    if not run_output:
        return json.dumps({"error": "找不到最近的运行记录"}, ensure_ascii=False)

    if not run_output.is_paused:
        return json.dumps(
            {"status": "not_paused", "message": "工作流未在暂停状态"},
            ensure_ascii=False,
        )

    for req in run_output.steps_requiring_confirmation:
        req.confirm()

    new_output = wf.continue_run(run_output, session_id=session_id)

    return json.dumps(_format_run_output(new_output, workflow_name), ensure_ascii=False)


@tool(stop_after_tool_call=True)
def reject_workflow_step(workflow_name: str, session_id: str) -> str:
    """拒绝当前暂停的工作流步骤。根据 on_reject 策略，可能跳过该步骤或取消整个工作流。

    Args:
        workflow_name: 工作流名称
        session_id: 工作流 session ID
    """
    wf = WORKFLOWS.get(workflow_name)
    if not wf:
        return json.dumps({"error": f"未知工作流: {workflow_name}"}, ensure_ascii=False)

    run_output = wf.get_last_run_output(session_id=session_id)
    if not run_output:
        return json.dumps({"error": "找不到最近的运行记录"}, ensure_ascii=False)

    if not run_output.is_paused:
        return json.dumps(
            {"status": "not_paused", "message": "工作流未在暂停状态"},
            ensure_ascii=False,
        )

    for req in run_output.steps_requiring_confirmation:
        req.reject()

    new_output = wf.continue_run(run_output, session_id=session_id)

    return json.dumps(_format_run_output(new_output, workflow_name), ensure_ascii=False)


@tool
def get_workflow_status(workflow_name: str, session_id: str) -> str:
    """查询工作流的当前状态。

    Args:
        workflow_name: 工作流名称
        session_id: 工作流 session ID
    """
    wf = WORKFLOWS.get(workflow_name)
    if not wf:
        return json.dumps({"error": f"未知工作流: {workflow_name}"}, ensure_ascii=False)

    run_output = wf.get_last_run_output(session_id=session_id)
    if not run_output:
        return json.dumps(
            {"status": "not_found", "message": f"找不到工作流 session: {session_id}"},
            ensure_ascii=False,
        )

    return json.dumps(_format_run_output(run_output, workflow_name), ensure_ascii=False)
