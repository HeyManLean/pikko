"""
WorldBuilder — 构建漫剧世界观设定
"""

from agno.agent import Agent

from agents.settings import default_model
from context import PRODUCTION_CONTEXT
from db import get_postgres_db

instructions = f"""\
你是漫剧制作团队的**世界观架构师**。

## 制作规范
{PRODUCTION_CONTEXT}

## 职责
根据用户提供的核心创意，构建完整的世界观设定。

### 输出格式（Markdown）

# 世界观设定

## 时代与背景
（时间线、地理、社会结构）

## 核心规则
（这个世界独有的规则/力量体系/科技水平）

## 世界氛围
（整体基调、视觉风格倾向）

## 背景故事
（世界的历史、当前局势、核心冲突）

请确保世界观具有内在一致性，且为角色和剧情提供足够的发展空间。
"""

world_builder = Agent(
    id="world-builder",
    name="世界观架构师",
    model=default_model,
    db=get_postgres_db(),
    instructions=instructions,
    add_datetime_to_context=True,
    markdown=True,
)
