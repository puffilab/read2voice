# EPUB TTS Server (Local / VPS)

这是服务端版本的文档朗读系统，支持：
- 默认本地匿名模式（无需注册/登录）
- 上传 EPUB/PDF/TXT/Word（`.docx`）、选章节、后台分段合成
- 多引擎 TTS（OpenAI / Edge TTS / 自定义 HTTP API）
- 合成后在线播放 + 下载音频
- 支持连续合成：可从当前章节自动合成到末章，并可边播边预合成下一章
- 支持历史音频列表：可回看历史任务并单独播放/下载/删除
- 音频命名按“书名-章节名”，重复章节会提示“已合成过”并复用历史任务
- 前端多语言：简体中文 / 繁體中文 / English / 日本語
- 前端设置保存在浏览器 Cookie（语言、TTS 参数、引擎配置）
- SQLite 持久化（默认 `data/app.sqlite3`），并兼容旧 JSON 数据自动迁移

## 快速启动

```bash
python -m pip install -r requirements.txt
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
```

浏览器访问：`http://127.0.0.1:8000`

## 关键特性

- `data/app.sqlite3` 落盘持久化（用户、文档、任务）
- `data/audio/` 存储音频文件
- 关键读取路径走 SQLite 实时查询（减少内存缓存不一致）
- 后台任务进度轮询
- 浏览器 Cookie 保存 TTS 配置（含 API Key）
- Voice 下拉自动按引擎刷新
- 合成完成后可点击“下载音频”

## API 概览

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET /api/profile/tts_config`
- `PUT /api/profile/tts_config`
- `GET /api/quota`
- `GET /api/engines`
- `GET /api/voices?engine=openai|edge_tts|custom_http`
- `POST /api/upload_epub`（接收 `.epub` / `.pdf` / `.txt` / `.docx`，`.doc` 需先转 `.docx`）
- `GET /api/documents/{doc_id}`
- `GET /api/documents/{doc_id}/chapters/{chapter_index}`
- `POST /api/synthesize`
- `POST /api/synthesize_jobs`
- `GET /api/synthesize_jobs/{job_id}`
- `GET /api/synthesize_jobs/{job_id}/audio`
- `GET /api/synthesize_jobs/{job_id}/download`
- `DELETE /api/synthesize_jobs/{job_id}`

## Docker + Nginx

```bash
docker compose up --build
```

访问：`http://127.0.0.1:8000`

默认把数据映射到本地 `./data` 目录。

## 环境变量

- `APP_DATA_DIR`：数据目录（默认 `./data`）
- `ENABLE_SIGNUP`：是否允许注册（`1`/`0`，默认 `1`）
- `TOKEN_TTL_SECONDS`：登录 token 有效期秒数（默认 7 天）
- `MAX_STORED_JOBS`：最多保留任务数量（默认 50）
- `ENABLE_MEMBERSHIP`：是否开启会员/配额/后台（`1`/`0`，默认 `0`）
