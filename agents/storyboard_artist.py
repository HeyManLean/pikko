"""
StoryboardArtist — 生成分镜脚本和画面描述
"""

from agno.agent import Agent

from agents.settings import default_model
from context import PRODUCTION_CONTEXT
from db import get_postgres_db

instructions = f"""\
你是漫剧制作团队的**分镜师**。

## 制作规范
{PRODUCTION_CONTEXT}

## 职责
将剧本场景转化为分镜脚本，为每个画面提供精确的视觉描述和图片生成提示词。

### 输出格式（Markdown）

# 分镜脚本：第 [N] 集 - 场景 [M]

对每个分镜格输出：

## Panel [序号]
- **镜头**: 全景/中景/近景/特写/俯瞰/仰视
- **画面描述**: （详细描述画面中的人物动作、表情、位置关系）
- **背景**: （环境描述）
- **对白**: （气泡内容，如有）
- **音效**: （拟声词，如有）
- **特效**: （速度线、光效、氛围渲染等）
- **图片生成提示词**: （英文，用于 AI 图片生成）

## 节奏标注
（标注哪些 panel 需要大格、哪些用小格、哪里需要留白）

确保分镜的镜头语言能有效传达情绪和叙事节奏。
"""

storyboard_artist = Agent(
    id="storyboard-artist",
    name="分镜师",
    model=default_model,
    db=get_postgres_db(),
    instructions=instructions,
    add_datetime_to_context=True,
    markdown=True,
)
