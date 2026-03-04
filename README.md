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

### Docker 部署（推荐）

#### 1. 安装 Docker（Ubuntu/Debian）

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin git
sudo systemctl enable --now docker
```

#### 2. 拉取项目并准备数据目录

```bash
git clone https://github.com/puffilab/read2voice.git
cd read2voice
mkdir -p data
```

#### 3. 启动服务

```bash
docker compose up -d --build
```

#### 4. 检查运行状态

```bash
docker compose ps
docker compose logs -f app
docker compose logs -f nginx
```

访问地址：`http://你的服务器IP:8000`  
默认 `docker-compose.yml` 使用 Nginx 对外暴露 `8000:80`。

#### 5. 数据持久化说明

- 宿主机 `./data` 挂载到容器 `/app/data`
- 数据库默认在 `data/app.sqlite3`
- 音频文件默认在 `data/audio/`

#### 6. 常用运维命令

```bash
# 停止并移除容器（不会删除 ./data）
docker compose down

# 重启服务
docker compose restart

# 更新代码并重建
git pull
docker compose up -d --build
```

```bash
# 备份数据目录
tar czf backup-data-$(date +%F).tar.gz data
```

#### GitHub Actions 自动推送 Docker 镜像

仓库已包含工作流文件：`.github/workflows/docker-publish.yml`。  
当你推送到 `main` 或推送 `v*` 标签时，会自动构建并推送镜像到 Docker Hub。

请在 GitHub 仓库里设置以下 Secrets：

- `DOCKERHUB_USERNAME`：你的 Docker Hub 用户名
- `DOCKERHUB_TOKEN`：Docker Hub Access Token（不要用密码）
- 并确认 Docker Hub 已存在仓库：`<DOCKERHUB_USERNAME>/read2voice`（建议先在网页创建 Public repository）
- `DOCKERHUB_TOKEN` 需要至少包含 `Read` + `Write` 权限

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

### Docker 部署（建議）

#### 1. 安裝 Docker（Ubuntu/Debian）

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin git
sudo systemctl enable --now docker
```

#### 2. 下載專案並建立資料目錄

```bash
git clone https://github.com/puffilab/read2voice.git
cd read2voice
mkdir -p data
```

#### 3. 啟動服務

```bash
docker compose up -d --build
```

#### 4. 檢查執行狀態

```bash
docker compose ps
docker compose logs -f app
docker compose logs -f nginx
```

瀏覽：`http://你的伺服器IP:8000`  
預設 `docker-compose.yml` 由 Nginx 對外提供 `8000:80`。

#### 5. 資料持久化說明

- 主機 `./data` 掛載到容器 `/app/data`
- 資料庫預設在 `data/app.sqlite3`
- 音訊檔案預設在 `data/audio/`

#### 6. 常用維運指令

```bash
# 停止並移除容器（不會刪除 ./data）
docker compose down

# 重新啟動
docker compose restart

# 更新程式碼並重建
git pull
docker compose up -d --build
```

```bash
# 備份資料目錄
tar czf backup-data-$(date +%F).tar.gz data
```

#### GitHub Actions 自動推送 Docker 映像

倉庫已包含工作流程檔：`.github/workflows/docker-publish.yml`。  
當你推送到 `main` 或推送 `v*` 標籤時，會自動建置並推送映像到 Docker Hub。

請在 GitHub 倉庫設定以下 Secrets：

- `DOCKERHUB_USERNAME`：你的 Docker Hub 使用者名稱
- `DOCKERHUB_TOKEN`：Docker Hub Access Token（不要使用密碼）
- 並確認 Docker Hub 已建立倉庫：`<DOCKERHUB_USERNAME>/read2voice`（建議先建立 Public repository）
- `DOCKERHUB_TOKEN` 至少需要 `Read` + `Write` 權限

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

### Docker Deployment (Recommended)

#### 1. Install Docker (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin git
sudo systemctl enable --now docker
```

#### 2. Clone the repo and prepare data directory

```bash
git clone https://github.com/puffilab/read2voice.git
cd read2voice
mkdir -p data
```

#### 3. Start containers

```bash
docker compose up -d --build
```

#### 4. Verify status and logs

```bash
docker compose ps
docker compose logs -f app
docker compose logs -f nginx
```

Open: `http://YOUR_SERVER_IP:8000`  
By default, `docker-compose.yml` exposes Nginx on `8000:80`.

#### 5. Data persistence

- Host `./data` is mounted to container `/app/data`
- SQLite database: `data/app.sqlite3`
- Audio files: `data/audio/`

#### 6. Common operations

```bash
# Stop and remove containers (keeps ./data)
docker compose down

# Restart services
docker compose restart

# Pull latest code and rebuild
git pull
docker compose up -d --build
```

```bash
# Backup data directory
tar czf backup-data-$(date +%F).tar.gz data
```

#### GitHub Actions Auto Push to Docker Hub

This repository now includes `.github/workflows/docker-publish.yml`.  
On pushes to `main` or tags matching `v*`, GitHub Actions will build and publish Docker images automatically.

Set these GitHub repository secrets first:

- `DOCKERHUB_USERNAME`: your Docker Hub username
- `DOCKERHUB_TOKEN`: a Docker Hub access token (use token, not password)
- Ensure the Docker Hub repository exists first: `<DOCKERHUB_USERNAME>/read2voice` (create a public repository in Docker Hub)
- The token should have at least `Read` + `Write` permissions

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

### Docker デプロイ（推奨）

#### 1. Docker をインストール（Ubuntu/Debian）

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin git
sudo systemctl enable --now docker
```

#### 2. リポジトリ取得とデータディレクトリ準備

```bash
git clone https://github.com/puffilab/read2voice.git
cd read2voice
mkdir -p data
```

#### 3. 起動

```bash
docker compose up -d --build
```

#### 4. 状態確認とログ確認

```bash
docker compose ps
docker compose logs -f app
docker compose logs -f nginx
```

アクセス：`http://サーバーIP:8000`  
既定では `docker-compose.yml` で Nginx が `8000:80` を公開します。

#### 5. データ永続化

- ホストの `./data` をコンテナ `/app/data` にマウント
- SQLite DB: `data/app.sqlite3`
- 音声ファイル: `data/audio/`

#### 6. よく使う運用コマンド

```bash
# 停止してコンテナ削除（./data は保持）
docker compose down

# 再起動
docker compose restart

# 最新コードを反映して再ビルド
git pull
docker compose up -d --build
```

```bash
# データディレクトリをバックアップ
tar czf backup-data-$(date +%F).tar.gz data
```

#### GitHub Actions で Docker Hub へ自動プッシュ

このリポジトリには `.github/workflows/docker-publish.yml` が含まれています。  
`main` への push、または `v*` タグ push 時に、Docker イメージを自動ビルドして Docker Hub へ公開します。

GitHub リポジトリの Secrets に以下を設定してください：

- `DOCKERHUB_USERNAME`：Docker Hub ユーザー名
- `DOCKERHUB_TOKEN`：Docker Hub の Access Token（パスワードではなくトークンを使用）
- Docker Hub 側で `<DOCKERHUB_USERNAME>/read2voice` リポジトリを事前作成してください（Public 推奨）
- `DOCKERHUB_TOKEN` には少なくとも `Read` + `Write` 権限が必要です

### 主な環境変数

- `APP_DATA_DIR`：データディレクトリ（既定 `./data`）
- `ENABLE_SIGNUP`：サインアップ許可（`1`/`0`）
- `TOKEN_TTL_SECONDS`：認証トークン有効期限（秒）
- `MAX_STORED_JOBS`：保持する合成ジョブの最大数
- `ENABLE_MEMBERSHIP`：会員/クォータ/管理機能の有効化（既定 `0`）
