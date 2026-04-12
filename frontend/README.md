# Biteagle Frontend

Web3 新闻分析平台前端应用。

## 技术栈

- **框架**: Next.js 15 (App Router)
- **UI**: React 19 + TypeScript
- **样式**: Tailwind CSS
- **组件库**: shadcn/ui

## 开发环境设置

```bash
# 安装依赖
npm install

# 配置环境变量
cp .env.local.example .env.local

# 启动开发服务器 (http://localhost:3000)
npm run dev
```

## 环境变量

```bash
# API 后端地址
NEXT_PUBLIC_API_URL=http://localhost:8000

# LangSmith 追踪 (可选)
NEXT_PUBLIC_LANGCHAIN_PROJECT=biteagle
```

## 项目结构

```
src/
├── app/              # Next.js App Router
│   ├── (dashboard)/  # 主应用页面
│   ├── api/          # API Routes (代理)
│   ├── layout.tsx    # 根布局
│   └── page.tsx      # 首页
├── components/       # React 组件
│   └── ui/          # shadcn/ui 组件
├── lib/             # 工具函数 & API 客户端
└── styles/          # 全局样式
```

## 后端 API 集成

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/health` | GET | 健康检查 |
| `/api/v1/analysis` | POST | 新闻分析 |
| `/api/v1/kg/projects/{name}` | GET | 知识图谱查询 |

## 可用脚本

| 命令 | 说明 |
|------|------|
| `npm run dev` | 启动开发服务器 |
| `npm run build` | 构建生产版本 |
| `npm start` | 启动生产服务器 |
| `npm run lint` | 运行 ESLint |

## 依赖服务

确保以下服务已启动：

- **Backend API**: http://localhost:8000
- **PostgreSQL**: localhost:5433
- **Redis**: localhost:6380
- **Neo4j**: localhost:7687
