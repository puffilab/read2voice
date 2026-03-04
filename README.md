# Read2Voice

[简体中文](#简体中文) | [繁體中文](#繁體中文) | [English](#english) | [日本語](#日本語)

---

## 简体中文

本项目是一个可部署在本地或 VPS 的文档转语音服务器，支持网页上传文档并调用多种 TTS 引擎进行朗读。

### 功能

- 默认本地匿名模式（无需注册/登录）
- 支持上传：`.epub` / `.pdf`（文本型）/ `.txt` / `.docx`
- `.doc` 会提示先转换为 `.docx`
- 章节浏览与章节朗读
- 支持连续合成（自动从当前章到末章）
- 历史音频可播放、下载、删除
- 已上传文件列表可查看、打开、删除（删除文件不会删除历史音频）
- 多语言前端：简体中文 / 繁體中文 / English / 日本語
- SQLite 持久化（默认 `data/app.sqlite3`）

### 快速启动（本地 Python）

```bash
python -m pip install -r requirements.txt
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
```

访问：`http://127.0.0.1:8000`

### Docker 启动

```bash
docker compose up --build -d
```

访问：`http://127.0.0.1:8000`

### 主要环境变量

- `APP_DATA_DIR`：数据目录（默认 `./data`）
- `ENABLE_SIGNUP`：是否允许注册（`1`/`0`）
- `TOKEN_TTL_SECONDS`：登录 token 过期时间（秒）
- `MAX_STORED_JOBS`：最多保留任务数
- `ENABLE_MEMBERSHIP`：是否启用会员/配额/后台（默认 `0`）

---

## 繁體中文

本專案是一個可部署在本機或 VPS 的文件轉語音伺服器，支援網頁上傳文件並使用多種 TTS 引擎朗讀。

### 功能

- 預設本機匿名模式（不需註冊/登入）
- 支援上傳：`.epub` / `.pdf`（文字型）/ `.txt` / `.docx`
- `.doc` 會提示先轉為 `.docx`
- 章節瀏覽與章節朗讀
- 支援連續合成（自動由目前章節合成到最後）
- 歷史音訊可播放、下載、刪除
- 已上傳文件清單可查看、開啟、刪除（刪除文件不會刪除歷史音訊）
- 前端多語系：简体中文 / 繁體中文 / English / 日本語
- SQLite 持久化（預設 `data/app.sqlite3`）

### 快速啟動（本機 Python）

```bash
python -m pip install -r requirements.txt
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
```

瀏覽：`http://127.0.0.1:8000`

### Docker 啟動

```bash
docker compose up --build -d
```

瀏覽：`http://127.0.0.1:8000`

### 主要環境變數

- `APP_DATA_DIR`：資料目錄（預設 `./data`）
- `ENABLE_SIGNUP`：是否允許註冊（`1`/`0`）
- `TOKEN_TTL_SECONDS`：登入 token 有效秒數
- `MAX_STORED_JOBS`：最多保留任務數
- `ENABLE_MEMBERSHIP`：是否啟用會員/配額/後台（預設 `0`）

---

## English

This project is a document-to-speech web server that can run locally or on a VPS.  
Users can upload documents from the browser and synthesize speech with selectable TTS engines.

### Features

- Local anonymous mode by default (no signup/login required)
- Supported uploads: `.epub` / `.pdf` (text-based) / `.txt` / `.docx`
- `.doc` is not parsed directly; convert to `.docx` first
- Chapter browsing and chapter-level synthesis
- Auto chain synthesis (from current chapter to the end)
- History audio playback, download, and delete
- Uploaded file list with open/delete actions (deleting a file does not delete history audio)
- Multilingual UI: Simplified Chinese / Traditional Chinese / English / Japanese
- SQLite persistence (default `data/app.sqlite3`)

### Quick Start (Python)

```bash
python -m pip install -r requirements.txt
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
```

Open: `http://127.0.0.1:8000`

### Quick Start (Docker)

```bash
docker compose up --build -d
```

Open: `http://127.0.0.1:8000`

### Main Environment Variables

- `APP_DATA_DIR`: data directory (default `./data`)
- `ENABLE_SIGNUP`: enable signup (`1`/`0`)
- `TOKEN_TTL_SECONDS`: auth token TTL in seconds
- `MAX_STORED_JOBS`: max stored synthesis jobs
- `ENABLE_MEMBERSHIP`: enable membership/quota/admin (default `0`)

---

## 日本語

このプロジェクトは、ローカルまたは VPS で動作するドキュメント音声化サーバーです。  
ブラウザから文書をアップロードし、複数の TTS エンジンで音声合成できます。

### 機能

- デフォルトでローカル匿名モード（登録/ログイン不要）
- 対応アップロード：`.epub` / `.pdf`（テキスト型）/ `.txt` / `.docx`
- `.doc` は直接解析せず、`.docx` への変換が必要
- 章の閲覧と章単位の音声合成
- 連続合成（現在の章から最終章まで）
- 履歴音声の再生・ダウンロード・削除
- アップロード済みファイル一覧の表示・開く・削除（ファイル削除時も履歴音声は保持）
- 多言語 UI：简体中文 / 繁體中文 / English / 日本語
- SQLite 永続化（デフォルト `data/app.sqlite3`）

### クイックスタート（Python）

```bash
python -m pip install -r requirements.txt
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
```

アクセス：`http://127.0.0.1:8000`

### クイックスタート（Docker）

```bash
docker compose up --build -d
```

アクセス：`http://127.0.0.1:8000`

### 主な環境変数

- `APP_DATA_DIR`：データディレクトリ（既定 `./data`）
- `ENABLE_SIGNUP`：サインアップ許可（`1`/`0`）
- `TOKEN_TTL_SECONDS`：認証トークン有効期限（秒）
- `MAX_STORED_JOBS`：保持する合成ジョブの最大数
- `ENABLE_MEMBERSHIP`：会員/クォータ/管理機能の有効化（既定 `0`）
