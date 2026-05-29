# Docker Compose 使用说明

这份配置适合把 ReadingHelper Agent 作为本地 Web 应用交给别人测试。测试者只需要安装 Docker Desktop，用一条命令启动前后端，然后在页面里的“设置”中填写自己的 DeepSeek API Key。

## 需要提前安装

- Docker Desktop
- Git

首次执行 `docker compose up --build` 时，Docker 会下载这些基础镜像和依赖：

- `python:3.11-slim`
- `node:20-alpine`
- `nginx:1.27-alpine`
- 后端 Python 依赖
- 前端 npm 依赖

这些下载只会在首次构建或依赖变化时发生。

## 快速启动

1. 克隆项目并进入目录：

```bash
git clone https://github.com/Handao-dao/ReadingHelper_Agent.git
cd ReadingHelper_Agent
```

2. 启动应用：

```bash
docker compose up --build
```

3. 打开浏览器：

```text
http://localhost:8080
```

4. 进入顶部导航的“设置”页面，填写 DeepSeek API Key 并保存。

后端健康检查地址：

```text
http://localhost:8000/api/health
```

## 数据保存位置

API Key 设置、SQLite 生词本和阅读历史会保存到本机目录：

```text
backend/data
```

停止或删除容器不会删除这个目录，所以设置、生词本和历史记录可以保留。

## 常用命令

停止服务：

```bash
docker compose down
```

后台运行：

```bash
docker compose up --build -d
```

查看日志：

```bash
docker compose logs -f
```

重新构建：

```bash
docker compose build --no-cache
```

## 端口

- 前端页面：`8080`
- 后端 API：`8000`

如果本机端口被占用，可以修改根目录的 `docker-compose.yml`：

```yaml
ports:
  - "8081:80"
```

修改后访问：

```text
http://localhost:8081
```

## 注意事项

- 如果仍然使用 `backend/.env` 作为本地后备配置，不要提交这个文件，里面可能包含 API Key。
- 首次构建需要网络访问 Docker Hub、PyPI 和 npm registry。
- 如果在中国大陆网络环境下构建较慢，建议配置 Docker Desktop 镜像加速，或换用更稳定的网络。
- Docker Compose 版本适合测试和部署，不等同于普通用户双击安装的桌面应用。
