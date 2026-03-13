# Pikko - 漫剧制作 Agent 系统

多智能体漫剧制作系统 — 通过对话式 Orchestrator 协调 7 位 AI 专家，完成漫画/条漫的全流程制作。

## 架构

```
用户 ←→ Orchestrator Agent（唯一入口）
            │
            ├── Tools Layer
            │   ├── project_tools    项目 CRUD
            │   ├── world_tools      WF1: 世界观/角色网络/大纲
            │   ├── character_tools  WF2: 角色设定/图片生成
            │   ├── episode_tools    WF3: 单集剧情/场景道具
            │   └── storyboard_tools WF4: 分镜/视频合成
            │
            ├── Specialist Agents（内部调用）
            │   ├── WorldBuilder        世界观架构师
            │   ├── CharacterArchitect  角色架构师
            │   ├── PlotDesigner        剧情设计师
            │   ├── CharacterArtist     角色美术师
            │   ├── EpisodeWriter       剧本作家
            │   ├── SceneDesigner       场景设计师
            │   └── StoryboardArtist    分镜师
            │
            └── PostgreSQL
                Projects / Worlds / Characters / Episodes / Storyboards
```

## 四条工作流

每步完成后暂停，等用户确认再继续。

| 工作流 | 步骤 | 用途 |
|--------|------|------|
| WF1 世界构建 | 创建项目 → 世界观 → 角色网络 → 剧情大纲 | 新项目必经 |
| WF2 角色设计 | 角色设定 → 角色设定图 | 为角色生成视觉 |
| WF3 单集制作 | 单集剧本 → 场景/道具/新角色 | 逐集创作 |
| WF4 分镜生成 | 分镜脚本 → 图片/视频 | 视觉产出 |

支持随时修改：修改角色、重写剧集、重新生成分镜。

## 快速开始

### 1. 配置

```sh
cp example.env .env
# 编辑 .env，填入 OPENAI_API_KEY
```

### 2. 启动服务

```sh
docker compose up -d --build
```

### 3. 连接 UI

1. 打开 [os.agno.com](https://os.agno.com) 并登录
2. 点击 **Add OS** → **Local** → 输入 `http://localhost:8000`
3. 点击 **Connect**

## 使用示例

```
我想创建一部校园恋爱条漫
```

Orchestrator 会自动引导你走完 WF1 世界构建流程，每步等你确认。

```
为女主角生成设定图
```

触发 WF2 角色设计流程。

```
编写第1集的剧本
```

触发 WF3 单集制作流程。

```
修改男主角的性格，改成更阳光开朗
```

直接调用修改工具更新角色。

## 项目结构

```
pikko/
├── agents/
│   ├── orchestrator.py           # 用户对话入口
│   ├── world_builder.py          # 世界观架构师
│   ├── character_architect.py    # 角色架构师
│   ├── plot_designer.py          # 剧情设计师
│   ├── character_artist.py       # 角色美术师
│   ├── episode_writer.py         # 剧本作家
│   ├── scene_designer.py         # 场景设计师
│   ├── storyboard_artist.py      # 分镜师
│   └── settings.py               # 共享配置
├── tools/
│   ├── project_tools.py          # 项目 CRUD
│   ├── world_tools.py            # WF1 工具
│   ├── character_tools.py        # WF2 工具
│   ├── episode_tools.py          # WF3 工具
│   └── storyboard_tools.py       # WF4 工具
├── models/
│   ├── base.py                   # SQLAlchemy Base
│   ├── project.py                # Project
│   ├── world.py                  # World + PlotOutline
│   ├── character.py              # Character
│   ├── episode.py                # Episode + Scene
│   └── storyboard.py             # StoryboardPanel + Video
├── context/
│   ├── production_guidelines.md  # 制作规范
│   ├── style_guide.md            # 风格指南
│   ├── workflow_rules.md         # 流程规则
│   └── loader.py                 # 加载上下文
├── db/
│   ├── session.py                # DB 连接 + SQLAlchemy session
│   └── url.py                    # 数据库 URL
├── app/
│   ├── main.py                   # AgentOS 入口
│   └── config.yaml               # UI 快速提示
├── compose.yaml                  # Docker Compose
├── Dockerfile
├── pyproject.toml
└── example.env
```

## 本地开发

```sh
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 创建虚拟环境并安装依赖
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# 启动 PostgreSQL
docker compose up -d pikko-db

# 运行应用
python -m app.main
```

## 环境变量

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `OPENAI_API_KEY` | 是 | — | OpenAI 模型 + 向量嵌入 |
| `RUNTIME_ENV` | 否 | `prd` | 设为 `dev` 开启热重载 |
| `DB_HOST` | 否 | `localhost` | PostgreSQL 主机 |
| `DB_PORT` | 否 | `5432` | PostgreSQL 端口 |
| `DB_USER` | 否 | `ai` | PostgreSQL 用户名 |
| `DB_PASS` | 否 | `ai` | PostgreSQL 密码 |
| `DB_DATABASE` | 否 | `ai` | PostgreSQL 数据库名 |
