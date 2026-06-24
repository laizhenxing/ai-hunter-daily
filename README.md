# 🤖 AI Hunter Daily

每日自动在 GitHub 上发现有意思的 **AI Agent / MCP Skill / AI 工具** 项目，自动评分、生成 Markdown 日报，并可通过 GitHub Actions 定时归档。

## 核心能力

- 🔍 **多维度搜索**：覆盖 AI Agent 框架、MCP Server/Skill、Agent 编排、轻量 AI 工具、AI API / 变现方向
- 📈 **热度评分**：基于 Stars 增速、Forks、近期更新、核心标签命中、变现/易用关键词综合打分
- 📝 **Markdown 日报**：每日生成结构化的候选项目报告
- ⏰ **自动运行**：支持 GitHub Actions 每天定时执行并提交报告

## 快速开始

### 1. 克隆并安装依赖

```bash
cd ai-hunter-daily
pip install -r requirements.txt
```

### 2. 本地运行

```bash
python run.py
```

推荐配置 GitHub Token 以提升 API 配额：

```bash
export GITHUB_TOKEN=your_github_token
python run.py
```

运行后会在 `reports/` 目录下生成 `YYYY-MM-DD.md` 日报文件。

## 项目结构

```
.
├── .github/workflows/daily.yml   # GitHub Actions 定时任务
├── config.yaml                   # 搜索与评分配置
├── requirements.txt
├── run.py                        # 本地入口
├── src/
│   ├── github_client.py          # GitHub API 封装
│   ├── scorer.py                 # 评分与去重
│   └── reporter.py               # Markdown 日报生成
└── reports/                      # 日报输出
```

## 自定义配置

编辑 `config.yaml` 即可调整：

- `search.queries`：增加/修改搜索关键词
- `scoring.weights`：调整评分权重
- `scoring.core_topics`：定义核心标签库
- `scoring.value_keywords`：定义变现/易用关键词库
- `scoring.top_n`：日报精选项目数量

## GitHub Actions 部署

项目已包含 `.github/workflows/daily.yml`，每日北京时间 09:07 自动运行。

### 设置步骤

1. 将本项目推送到你的 GitHub 仓库
2. 确保仓库 `Settings → Actions → General → Workflow permissions` 开启 `Read and write permissions`
3. （可选）在 `Settings → Secrets and variables → Actions` 添加 `GITHUB_TOKEN`（通常默认已存在，无需额外创建）
4. 可手动触发一次 `Actions → AI Hunter Daily → Run workflow` 验证

## API 配额说明

| 类型 | 请求配额 |
|------|---------|
| 未认证 | 10 次/分钟 |
| 已认证（GITHUB_TOKEN） | 30 次/分钟 |

建议始终配置 `GITHUB_TOKEN`，否则容易触发速率限制。

## 评分逻辑

综合得分 = 各维度加权求和

| 维度 | 说明 |
|------|------|
| 7 日 Star 增速 | 日均 Star 增量 × 7，封顶 100 |
| 24h Star 增速 | 日均 Star 增量，封顶 50 |
| Forks | 每 10 个 fork 1 分，封顶 50 |
| 近期更新 | 30 天内更新得 30 分 |
| Topic 命中 | 命中核心标签每个 10 分，封顶 50 |
| 关键词命中 | 名称/描述命中变现/易用关键词每个 10 分，封顶 50 |

## 免责声明

本项目仅做信息聚合与自动化发现，不构成任何投资建议。所有项目信息均来自 GitHub 公开 API。
