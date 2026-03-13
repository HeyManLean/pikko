"""
Character CRUD tools for the orchestrator.
"""

import json

from agno.tools import tool

from db import get_session
from models.character import Character


@tool
def update_character(character_id: str, field: str, value: str) -> str:
    """更新角色的某个字段。

    Args:
        character_id: 角色 ID
        field: 要更新的字段名（name/role/personality/appearance/relationships）
        value: 新的值
    """
    allowed_fields = {"name", "role", "personality", "appearance", "relationships"}
    if field not in allowed_fields:
        return json.dumps({"error": f"不支持的字段: {field}，可选: {allowed_fields}"}, ensure_ascii=False)

    with get_session() as session:
        char = session.get(Character, character_id)
        if not char:
            return json.dumps({"error": f"角色 {character_id} 不存在"}, ensure_ascii=False)

        setattr(char, field, value)
        return json.dumps({
            "status": "success",
            "character_id": char.id,
            "updated_field": field,
            "new_value": value,
        }, ensure_ascii=False)


@tool
def list_characters(project_id: str) -> str:
    """列出项目下的所有角色。

    Args:
        project_id: 项目 ID
    """
    with get_session() as session:
        chars = session.query(Character).filter_by(project_id=project_id).all()
        result = [
            {
                "id": c.id,
                "name": c.name,
                "role": c.role,
                "personality": c.personality,
                "has_image": bool(c.image_url),
            }
            for c in chars
        ]
        return json.dumps(result, ensure_ascii=False)
