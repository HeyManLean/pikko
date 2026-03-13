"""
Markdown output parsers for LLM agent responses.

Each parser extracts structured data from the semi-structured markdown
that domain agents (character_architect, scene_designer, storyboard_artist,
plot_designer) produce.
"""

from __future__ import annotations

import re


def parse_characters(text: str) -> list[dict[str, str]]:
    """Parse character_architect markdown into character dicts.

    Expected format per character:
        ## 角色：名字
        - **定位**: ...
        - **性格**: ...
        - **外观概述**: ...
        - **与其他角色的关系**: ...
    """
    characters: list[dict[str, str]] = []
    sections = re.split(r"##\s*角色[：:]\s*", text)

    field_map = {
        "定位": "role",
        "性格": "personality",
        "外观": "appearance",
        "外观概述": "appearance",
        "关系": "relationships",
        "与其他角色的关系": "relationships",
    }

    for section in sections[1:]:
        lines = section.strip().split("\n")
        name = lines[0].strip().rstrip("*# ")
        if not name:
            continue
        char: dict[str, str] = {"name": name}
        for line in lines[1:]:
            line = line.strip()
            if not line.startswith("- **"):
                continue
            m = re.match(r"-\s*\*\*([^*]+)\*\*[：:]\s*(.*)", line)
            if not m:
                continue
            label, value = m.group(1).strip(), m.group(2).strip()
            for prefix, key in field_map.items():
                if label.startswith(prefix):
                    char[key] = value
                    break
        characters.append(char)

    return characters


def parse_scenes_from_script(text: str) -> list[dict[str, str]]:
    """Parse episode_writer markdown into scene dicts.

    Expected format:
        ### 场景 1：场景名
        - **地点**: ...
        - **出场角色**: ...
        - **道具**: ...
        **剧情描述**: ...
        **对白**: ...
    """
    scenes: list[dict[str, str]] = []
    sections = re.split(r"###\s*场景\s*(\d+)[：:]\s*", text)

    i = 1
    while i < len(sections) - 1:
        number_str = sections[i]
        body = sections[i + 1]
        i += 2

        scene: dict[str, str] = {"number": number_str}

        first_line = body.strip().split("\n")[0].strip()
        if not first_line.startswith("-") and not first_line.startswith("*"):
            scene["name"] = first_line.rstrip("*# ")

        location_m = re.search(r"\*\*地点\*\*[：:]\s*(.+)", body)
        if location_m:
            scene["location"] = location_m.group(1).strip()

        chars_m = re.search(r"\*\*出场角色\*\*[：:]\s*(.+)", body)
        if chars_m:
            scene["characters_involved"] = chars_m.group(1).strip()

        props_m = re.search(r"\*\*道具\*\*[：:]\s*(.+)", body)
        if props_m:
            scene["props"] = props_m.group(1).strip()

        dialogue_m = re.search(
            r"\*\*对白\*\*[：:]?\s*\n([\s\S]*?)(?=\n###|\n##|\n\*\*|\Z)", body
        )
        if dialogue_m:
            scene["dialogue"] = dialogue_m.group(1).strip()

        desc_m = re.search(
            r"\*\*剧情描述\*\*[：:]?\s*\n([\s\S]*?)(?=\n\*\*对白|\n###|\n##|\Z)", body
        )
        if desc_m:
            scene["description"] = desc_m.group(1).strip()
        else:
            scene["description"] = body.strip()[:500]

        scenes.append(scene)

    return scenes


def parse_panels(text: str) -> list[dict[str, str]]:
    """Parse storyboard_artist markdown into panel dicts.

    Expected format:
        ## Panel 1
        - **镜头**: ...
        - **画面描述**: ...
        - **对白**: ...
        - **音效**: ...
        - **图片生成提示词**: ...
    """
    panels: list[dict[str, str]] = []
    sections = re.split(r"##\s*Panel\s*(\d+)", text, flags=re.IGNORECASE)

    field_map = {
        "镜头": "camera_angle",
        "画面描述": "description",
        "对白": "dialogue",
        "音效": "sfx",
        "特效": "sfx",
        "图片生成提示词": "image_prompt",
    }

    i = 1
    while i < len(sections) - 1:
        number_str = sections[i]
        body = sections[i + 1]
        i += 2

        panel: dict[str, str] = {"number": number_str}
        for line in body.strip().split("\n"):
            line = line.strip()
            if not line.startswith("- **"):
                continue
            m = re.match(r"-\s*\*\*([^*]+)\*\*[：:]\s*(.*)", line)
            if not m:
                continue
            label, value = m.group(1).strip(), m.group(2).strip()
            for prefix, key in field_map.items():
                if label.startswith(prefix):
                    panel[key] = value
                    break

        if not panel.get("description"):
            desc_m = re.search(
                r"\*\*画面描述\*\*[：:]?\s*\n([\s\S]*?)(?=\n-\s*\*\*|\n##|\Z)", body
            )
            if desc_m:
                panel["description"] = desc_m.group(1).strip()

        if not panel.get("image_prompt"):
            prompt_m = re.search(
                r"\*\*图片生成提示词\*\*[：:]?\s*\n([\s\S]*?)(?=\n##|\Z)", body
            )
            if prompt_m:
                raw = prompt_m.group(1).strip()
                raw = re.sub(r"^```\w*\n?|```$", "", raw).strip()
                panel["image_prompt"] = raw

        panels.append(panel)

    return panels


def parse_plot_outline(text: str) -> dict[str, str | int | None]:
    """Parse plot_designer markdown into structured dict.

    Returns dict with keys: synopsis, themes, arc_structure, total_episodes.
    """
    result: dict[str, str | int | None] = {
        "synopsis": None,
        "themes": None,
        "arc_structure": None,
        "total_episodes": None,
    }

    section_pattern = r"##\s*(.+?)\n([\s\S]*?)(?=\n##|\Z)"
    for m in re.finditer(section_pattern, text):
        header = m.group(1).strip()
        body = m.group(2).strip()

        if "主题" in header or "核心主题" in header:
            result["themes"] = body
        elif "概要" in header or "故事概要" in header:
            result["synopsis"] = body
        elif "弧线" in header or "故事弧线" in header:
            result["arc_structure"] = body
        elif "总集数" in header or "建议总集数" in header:
            result["arc_structure"] = (
                result.get("arc_structure") or ""
            )
            num_m = re.search(r"(\d+)\s*集", body)
            if num_m:
                result["total_episodes"] = int(num_m.group(1))

    if not result["synopsis"]:
        result["synopsis"] = text

    return result
