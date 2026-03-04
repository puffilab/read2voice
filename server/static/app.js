let currentDocId = null;
let currentChapters = [];
let currentAudioUrl = null;
let currentPlayingJobId = "";

let appEnabled = false;
let synthesisInProgress = false;
let chainRunning = false;
let chainStopRequested = false;
let resolvePlaybackWait = null;

const GUEST_TOKEN = "__guest__";
let authToken = GUEST_TOKEN;
let currentUsername = "local";
let currentUserTier = "free";
let currentUserIsAdmin = false;
let profileConfigs = {};

const authUsername = document.getElementById("authUsername");
const authPassword = document.getElementById("authPassword");
const registerBtn = document.getElementById("registerBtn");
const loginBtn = document.getElementById("loginBtn");
const logoutBtn = document.getElementById("logoutBtn");
const authStatus = document.getElementById("authStatus");
const quotaStatus = document.getElementById("quotaStatus");
const languageSelect = document.getElementById("languageSelect");
const authCard = document.querySelector(".account-card");

const epubFile = document.getElementById("epubFile");
const uploadBtn = document.getElementById("uploadBtn");
let refreshDocsBtn = document.getElementById("refreshDocsBtn");
const uploadStatus = document.getElementById("uploadStatus");
let documentsList = document.getElementById("documentsList");
const chapterSelect = document.getElementById("chapterSelect");
const chapterText = document.getElementById("chapterText");

const engine = document.getElementById("engine");
const apiKey = document.getElementById("apiKey");
const endpoint = document.getElementById("endpoint");
const model = document.getElementById("model");
const voiceSelect = document.getElementById("voiceSelect");
const voiceCustom = document.getElementById("voiceCustom");
const speed = document.getElementById("speed");
const outputFormat = document.getElementById("outputFormat");
const instructions = document.getElementById("instructions");
const customHeaders = document.getElementById("customHeaders");

const saveProfileBtn = document.getElementById("saveProfileBtn");
const loadProfileBtn = document.getElementById("loadProfileBtn");
const downloadLink = document.getElementById("downloadLink");

const synthesizeChapterBtn = document.getElementById("synthesizeChapterBtn");
const synthesizeTextBtn = document.getElementById("synthesizeTextBtn");
const chainStartBtn = document.getElementById("chainStartBtn");
const chainStopBtn = document.getElementById("chainStopBtn");
const prefetchNextToggle = document.getElementById("prefetchNextToggle");

const ttsStatus = document.getElementById("ttsStatus");
const player = document.getElementById("player");
const ttsProgress = document.getElementById("ttsProgress");
const ttsProgressText = document.getElementById("ttsProgressText");
const refreshHistoryBtn = document.getElementById("refreshHistoryBtn");
const historyList = document.getElementById("historyList");
const adminPanel = document.getElementById("adminPanel");
const adminPlanSelect = document.getElementById("adminPlanSelect");
const adminPlanUploads = document.getElementById("adminPlanUploads");
const adminPlanSynths = document.getElementById("adminPlanSynths");
const adminSavePlanBtn = document.getElementById("adminSavePlanBtn");
const adminPlanStatus = document.getElementById("adminPlanStatus");
const adminUsersList = document.getElementById("adminUsersList");
let docsRefreshBound = false;

const I18N = {
  "zh-CN": {
    ui: {
      docTitle: "EPUB/PDF/TXT/Word 语音服务器",
      accountTitle: "账号",
      languageLabel: "语言",
      usernamePlaceholder: "用户名 (3-32位)",
      passwordPlaceholder: "密码 (至少6位)",
      registerBtn: "注册",
      loginBtn: "登录",
      logoutBtn: "退出",
      appTitle: "文档语音服务器",
      appSubTitle: "部署在本地或 VPS，通过网页上传 EPUB/PDF/TXT/Word 并调用可选 TTS 引擎。",
      uploadBtn: "上传文档",
      chapterPanelTitle: "章节",
      textPanelTitle: "正文",
      ttsConfigTitle: "TTS 引擎配置",
      labelEngine: "引擎",
      labelApiKey: "API Key",
      labelEndpoint: "Endpoint",
      labelModel: "Model",
      labelVoiceSelect: "Voice (自动下拉)",
      labelVoiceCustom: "Voice 手动覆盖 (可选)",
      labelSpeed: "Speed (0.25 - 4.0)",
      labelOutputFormat: "Output format",
      labelInstructions: "Instructions (OpenAI 可选)",
      labelCustomHeaders: "Custom headers JSON (仅自定义HTTP)",
      apiKeyPlaceholder: "OpenAI/第三方 API Key",
      endpointPlaceholder: "可选。OpenAI默认 /v1/audio/speech",
      modelPlaceholder: "如 gpt-4o-mini-tts",
      voiceCustomPlaceholder: "为空则用下拉选项",
      instructionsPlaceholder: "如 温柔、平稳地朗读",
      customHeadersPlaceholder: "{\"X-API-Key\":\"xxx\"}",
      synthesizeChapterBtn: "合成选中章节",
      synthesizeTextBtn: "合成文本框内容",
      chainStartBtn: "连续合成到末章",
      chainStopBtn: "停止连续",
      saveProfileBtn: "保存账号配置",
      loadProfileBtn: "读取账号配置",
      prefetchNextLabel: "播放时预合成下一章",
      downloadLink: "下载音频",
      documentsTitle: "已上传文件",
      refreshDocsBtn: "刷新文件列表",
      historyTitle: "历史音频",
      refreshHistoryBtn: "刷新历史",
      quotaStatusPrefix: "额度",
      adminTitle: "后台管理",
      adminPlansTitle: "会员等级额度",
      adminUsersTitle: "用户等级管理",
      adminSavePlanBtn: "保存等级额度",
      engineOpenai: "OpenAI TTS",
      engineEdge: "Edge TTS (免费)",
      engineCustom: "自定义 HTTP API",
    },
    msg: {
      notLoggedIn: "未登录",
      waitingUpload: "等待上传",
      waitingSynthesis: "等待合成",
      historyEmpty: "暂无历史音频",
      loginFirst: "请先登录",
      downloadFailed: "下载失败",
      deleteFailed: "删除失败",
      historyDeleted: "已删除历史音频",
      historyLoadFailed: "加载历史失败",
      noVoicesManualInput: "无可用语音，请手动输入",
      sessionExpiredRelogin: "登录已失效，请重新登录",
      loadVoicesFailed: "加载语音列表失败",
      loadProfileFailed: "读取账号配置失败",
      pleaseLogin: "请先登录",
      saveProfileFailed: "保存账号配置失败",
      profileSavedUser: "已保存账号配置（{username}）",
      profileLoadedUser: "已读取账号配置（{username}）",
      enterUserPass: "请输入用户名和密码",
      authFailed: "认证失败",
      loggedInUser: "已登录：{username}",
      uploadPickFile: "请选择 .epub / .pdf / .txt / .docx 文件",
      uploadingParsing: "上传并解析中...",
      uploadFailed: "上传失败",
      chapterOption: "[{index}] {title} ({length}字)",
      loadedChapterCountFilename: "已加载 {count} 章: {filename}",
      loadChapterFailed: "读取章节失败",
      submitJobFailed: "任务提交失败",
      audioFetchFailed: "音频下载失败",
      queryJobFailed: "查询任务状态失败",
      queueWaitingPrefix: "{prefix}排队中，等待前一个任务完成...",
      synthesizingProgressPrefix: "{prefix}合成中... {done}/{total} 段",
      synthFailed: "合成失败",
      stoppingChain: "正在停止连续合成...",
      taskInProgress: "已有任务在进行中，请稍候...",
      uploadAndChooseChapter: "请先上传文档并选择章节",
      chooseStartChapter: "请选择起始章节",
      chapterPrefix: "第{index}章：",
      playingAndPrefetch: "正在播放第{current}章，预合成第{next}章...",
      playingChapter: "正在播放第{index}章...",
      reachedLastChapter: "已连续合成并播放到最后一章",
      chainStopped: "连续合成已停止",
      uploadOrInputPrompt: "请先上传 EPUB/PDF/TXT/Word 或输入文本",
      submittingJob: "正在提交任务...",
      duplicateSynthDefault: "该章节已合成过",
      duplicateConfirm: "{tip}\n\n点击“确定”重新合成；点击“取消”直接播放历史音频。",
      replayExisting: "{tip}，正在播放历史音频...",
      synthDoneChunks: "合成完成，分段数: {chunks}",
      loggedOut: "已退出",
      customText: "自定义文本",
      unnamedBook: "未命名书籍",
      chapterShort: "章节 {index}",
      chapterTitleWithBook: "{book} · 章节 {index}{suffix}",
      chapterTitleNoBook: "章节 {index}{suffix}",
      confirmDelete: "确定删除这条历史音频吗？\n{title}",
      actionPlay: "播放",
      actionDownload: "下载",
      actionDelete: "删除",
      quotaLine: "额度: {tier} | 上传 {upUsed}/{upLimit} | 合成 {syUsed}/{syLimit}",
      unlimited: "不限",
      adminPlanSaved: "会员等级额度已保存",
      adminPlanSaveFailed: "保存会员等级额度失败",
      adminUsersLoadFailed: "加载用户列表失败",
      adminPlanLoadFailed: "加载会员等级失败",
      adminUserTierUpdated: "用户等级已更新",
      adminUserTierUpdateFailed: "更新用户等级失败",
      adminWaiting: "等待操作",
      adminChooseTier: "请选择等级",
      adminSaveUserTier: "保存用户等级",
      adminMonthUsage: "本月上传 {upUsed}/{upLimit} · 合成 {syUsed}/{syLimit}",
      adminIsAdmin: "管理员",
      docsEmpty: "暂无已上传文件",
      docsLoadFailed: "加载文件列表失败",
      actionOpen: "打开",
      actionDeleteDoc: "删除文件",
      confirmDeleteDoc: "确定删除文件吗？\n{filename}\n\n历史音频会保留。",
      docDeleted: "文件已删除：{filename}",
    },
  },
  "zh-TW": {
    ui: {
      docTitle: "EPUB/PDF/TXT/Word 語音伺服器",
      accountTitle: "帳號",
      languageLabel: "語言",
      usernamePlaceholder: "使用者名稱 (3-32字元)",
      passwordPlaceholder: "密碼 (至少6位)",
      registerBtn: "註冊",
      loginBtn: "登入",
      logoutBtn: "登出",
      appTitle: "文件語音伺服器",
      appSubTitle: "可部署於本機或 VPS，透過網頁上傳 EPUB/PDF/TXT/Word 並呼叫可選 TTS 引擎。",
      uploadBtn: "上傳文件",
      chapterPanelTitle: "章節",
      textPanelTitle: "正文",
      ttsConfigTitle: "TTS 引擎設定",
      labelEngine: "引擎",
      labelApiKey: "API Key",
      labelEndpoint: "Endpoint",
      labelModel: "Model",
      labelVoiceSelect: "Voice (自動下拉)",
      labelVoiceCustom: "Voice 手動覆寫 (可選)",
      labelSpeed: "Speed (0.25 - 4.0)",
      labelOutputFormat: "Output format",
      labelInstructions: "Instructions (OpenAI 可選)",
      labelCustomHeaders: "Custom headers JSON (僅自訂HTTP)",
      apiKeyPlaceholder: "OpenAI/第三方 API Key",
      endpointPlaceholder: "可選。OpenAI 預設 /v1/audio/speech",
      modelPlaceholder: "例如 gpt-4o-mini-tts",
      voiceCustomPlaceholder: "留空則使用下拉選項",
      instructionsPlaceholder: "例如 溫柔、平穩地朗讀",
      customHeadersPlaceholder: "{\"X-API-Key\":\"xxx\"}",
      synthesizeChapterBtn: "合成選中章節",
      synthesizeTextBtn: "合成文字框內容",
      chainStartBtn: "連續合成到末章",
      chainStopBtn: "停止連續",
      saveProfileBtn: "儲存帳號設定",
      loadProfileBtn: "讀取帳號設定",
      prefetchNextLabel: "播放時預合成下一章",
      downloadLink: "下載音訊",
      documentsTitle: "已上傳文件",
      refreshDocsBtn: "重新整理文件列表",
      historyTitle: "歷史音訊",
      refreshHistoryBtn: "重新整理歷史",
      quotaStatusPrefix: "額度",
      adminTitle: "後台管理",
      adminPlansTitle: "會員等級額度",
      adminUsersTitle: "使用者等級管理",
      adminSavePlanBtn: "儲存等級額度",
      engineOpenai: "OpenAI TTS",
      engineEdge: "Edge TTS (免費)",
      engineCustom: "自訂 HTTP API",
    },
    msg: {
      notLoggedIn: "未登入",
      waitingUpload: "等待上傳",
      waitingSynthesis: "等待合成",
      historyEmpty: "暫無歷史音訊",
      loginFirst: "請先登入",
      downloadFailed: "下載失敗",
      deleteFailed: "刪除失敗",
      historyDeleted: "已刪除歷史音訊",
      historyLoadFailed: "載入歷史失敗",
      noVoicesManualInput: "沒有可用語音，請手動輸入",
      sessionExpiredRelogin: "登入已失效，請重新登入",
      loadVoicesFailed: "載入語音清單失敗",
      loadProfileFailed: "讀取帳號設定失敗",
      pleaseLogin: "請先登入",
      saveProfileFailed: "儲存帳號設定失敗",
      profileSavedUser: "已儲存帳號設定（{username}）",
      profileLoadedUser: "已讀取帳號設定（{username}）",
      enterUserPass: "請輸入使用者名稱和密碼",
      authFailed: "認證失敗",
      loggedInUser: "已登入：{username}",
      uploadPickFile: "請選擇 .epub / .pdf / .txt / .docx 檔案",
      uploadingParsing: "上傳並解析中...",
      uploadFailed: "上傳失敗",
      chapterOption: "[{index}] {title} ({length}字)",
      loadedChapterCountFilename: "已載入 {count} 章: {filename}",
      loadChapterFailed: "讀取章節失敗",
      submitJobFailed: "任務提交失敗",
      audioFetchFailed: "音訊下載失敗",
      queryJobFailed: "查詢任務狀態失敗",
      queueWaitingPrefix: "{prefix}排隊中，等待前一個任務完成...",
      synthesizingProgressPrefix: "{prefix}合成中... {done}/{total} 段",
      synthFailed: "合成失敗",
      stoppingChain: "正在停止連續合成...",
      taskInProgress: "已有任務進行中，請稍候...",
      uploadAndChooseChapter: "請先上傳文件並選擇章節",
      chooseStartChapter: "請選擇起始章節",
      chapterPrefix: "第{index}章：",
      playingAndPrefetch: "正在播放第{current}章，預合成第{next}章...",
      playingChapter: "正在播放第{index}章...",
      reachedLastChapter: "已連續合成並播放到最後一章",
      chainStopped: "連續合成已停止",
      uploadOrInputPrompt: "請先上傳 EPUB/PDF/TXT/Word 或輸入文字",
      submittingJob: "正在提交任務...",
      duplicateSynthDefault: "此章節已合成過",
      duplicateConfirm: "{tip}\n\n點擊「確定」重新合成；點擊「取消」直接播放歷史音訊。",
      replayExisting: "{tip}，正在播放歷史音訊...",
      synthDoneChunks: "合成完成，分段數: {chunks}",
      loggedOut: "已登出",
      customText: "自訂文字",
      unnamedBook: "未命名書籍",
      chapterShort: "章節 {index}",
      chapterTitleWithBook: "{book} · 章節 {index}{suffix}",
      chapterTitleNoBook: "章節 {index}{suffix}",
      confirmDelete: "確定刪除這筆歷史音訊嗎？\n{title}",
      actionPlay: "播放",
      actionDownload: "下載",
      actionDelete: "刪除",
      quotaLine: "額度: {tier} | 上傳 {upUsed}/{upLimit} | 合成 {syUsed}/{syLimit}",
      unlimited: "不限",
      adminPlanSaved: "會員等級額度已儲存",
      adminPlanSaveFailed: "儲存會員等級額度失敗",
      adminUsersLoadFailed: "載入使用者列表失敗",
      adminPlanLoadFailed: "載入會員等級失敗",
      adminUserTierUpdated: "使用者等級已更新",
      adminUserTierUpdateFailed: "更新使用者等級失敗",
      adminWaiting: "等待操作",
      adminChooseTier: "請選擇等級",
      adminSaveUserTier: "儲存使用者等級",
      adminMonthUsage: "本月上傳 {upUsed}/{upLimit} · 合成 {syUsed}/{syLimit}",
      adminIsAdmin: "管理員",
      docsEmpty: "暫無已上傳文件",
      docsLoadFailed: "載入文件列表失敗",
      actionOpen: "開啟",
      actionDeleteDoc: "刪除文件",
      confirmDeleteDoc: "確定刪除文件嗎？\n{filename}\n\n歷史音訊會保留。",
      docDeleted: "文件已刪除：{filename}",
    },
  },
  "en-US": {
    ui: {
      docTitle: "EPUB/PDF/TXT/Word Voice Server",
      accountTitle: "Account",
      languageLabel: "Language",
      usernamePlaceholder: "Username (3-32 chars)",
      passwordPlaceholder: "Password (min 6 chars)",
      registerBtn: "Register",
      loginBtn: "Login",
      logoutBtn: "Logout",
      appTitle: "Document Voice Server",
      appSubTitle: "Run locally or on a VPS, upload EPUB/PDF/TXT/Word, and synthesize with selectable TTS engines.",
      uploadBtn: "Upload Document",
      chapterPanelTitle: "Chapters",
      textPanelTitle: "Text",
      ttsConfigTitle: "TTS Engine Config",
      labelEngine: "Engine",
      labelApiKey: "API Key",
      labelEndpoint: "Endpoint",
      labelModel: "Model",
      labelVoiceSelect: "Voice (Auto List)",
      labelVoiceCustom: "Voice Override (Optional)",
      labelSpeed: "Speed (0.25 - 4.0)",
      labelOutputFormat: "Output format",
      labelInstructions: "Instructions (OpenAI optional)",
      labelCustomHeaders: "Custom headers JSON (Custom HTTP only)",
      apiKeyPlaceholder: "OpenAI/3rd-party API Key",
      endpointPlaceholder: "Optional. OpenAI default: /v1/audio/speech",
      modelPlaceholder: "e.g. gpt-4o-mini-tts",
      voiceCustomPlaceholder: "Leave empty to use dropdown voice",
      instructionsPlaceholder: "e.g. Read gently and steadily",
      customHeadersPlaceholder: "{\"X-API-Key\":\"xxx\"}",
      synthesizeChapterBtn: "Synthesize Selected Chapter",
      synthesizeTextBtn: "Synthesize Text Box",
      chainStartBtn: "Auto Chain to End",
      chainStopBtn: "Stop Chain",
      saveProfileBtn: "Save Profile Config",
      loadProfileBtn: "Load Profile Config",
      prefetchNextLabel: "Prefetch next chapter while playing",
      downloadLink: "Download Audio",
      documentsTitle: "Uploaded Files",
      refreshDocsBtn: "Refresh File List",
      historyTitle: "Audio History",
      refreshHistoryBtn: "Refresh History",
      quotaStatusPrefix: "Quota",
      adminTitle: "Admin Console",
      adminPlansTitle: "Tier Quotas",
      adminUsersTitle: "User Tier Management",
      adminSavePlanBtn: "Save Tier Quota",
      engineOpenai: "OpenAI TTS",
      engineEdge: "Edge TTS (Free)",
      engineCustom: "Custom HTTP API",
    },
    msg: {
      notLoggedIn: "Not logged in",
      waitingUpload: "Waiting for upload",
      waitingSynthesis: "Waiting for synthesis",
      historyEmpty: "No audio history yet",
      loginFirst: "Please log in first",
      downloadFailed: "Download failed",
      deleteFailed: "Delete failed",
      historyDeleted: "History audio deleted",
      historyLoadFailed: "Failed to load history",
      noVoicesManualInput: "No voices available, enter one manually",
      sessionExpiredRelogin: "Session expired, please log in again",
      loadVoicesFailed: "Failed to load voices",
      loadProfileFailed: "Failed to load profile config",
      pleaseLogin: "Please log in first",
      saveProfileFailed: "Failed to save profile config",
      profileSavedUser: "Profile config saved ({username})",
      profileLoadedUser: "Profile config loaded ({username})",
      enterUserPass: "Please enter username and password",
      authFailed: "Authentication failed",
      loggedInUser: "Logged in: {username}",
      uploadPickFile: "Please select a .epub / .pdf / .txt / .docx file",
      uploadingParsing: "Uploading and parsing...",
      uploadFailed: "Upload failed",
      chapterOption: "[{index}] {title} ({length} chars)",
      loadedChapterCountFilename: "Loaded {count} chapters: {filename}",
      loadChapterFailed: "Failed to load chapter",
      submitJobFailed: "Failed to submit job",
      audioFetchFailed: "Failed to fetch audio",
      queryJobFailed: "Failed to query job status",
      queueWaitingPrefix: "{prefix}Queued, waiting for previous job...",
      synthesizingProgressPrefix: "{prefix}Synthesizing... {done}/{total} chunks",
      synthFailed: "Synthesis failed",
      stoppingChain: "Stopping auto chain...",
      taskInProgress: "A task is already running, please wait...",
      uploadAndChooseChapter: "Please upload a document and select a chapter first",
      chooseStartChapter: "Please choose a start chapter",
      chapterPrefix: "Chapter {index}: ",
      playingAndPrefetch: "Playing chapter {current}, pre-synthesizing chapter {next}...",
      playingChapter: "Playing chapter {index}...",
      reachedLastChapter: "Reached final chapter in auto chain",
      chainStopped: "Auto chain stopped",
      uploadOrInputPrompt: "Please upload EPUB/PDF/TXT/Word or input text first",
      submittingJob: "Submitting job...",
      duplicateSynthDefault: "This chapter has already been synthesized",
      duplicateConfirm: "{tip}\n\nPress OK to synthesize again, or Cancel to play existing audio.",
      replayExisting: "{tip}, playing existing audio...",
      synthDoneChunks: "Synthesis completed, chunks: {chunks}",
      loggedOut: "Logged out",
      customText: "Custom text",
      unnamedBook: "Untitled book",
      chapterShort: "Chapter {index}",
      chapterTitleWithBook: "{book} · Chapter {index}{suffix}",
      chapterTitleNoBook: "Chapter {index}{suffix}",
      confirmDelete: "Delete this history audio?\n{title}",
      actionPlay: "Play",
      actionDownload: "Download",
      actionDelete: "Delete",
      quotaLine: "Quota: {tier} | Upload {upUsed}/{upLimit} | Synthesize {syUsed}/{syLimit}",
      unlimited: "Unlimited",
      adminPlanSaved: "Tier quota saved",
      adminPlanSaveFailed: "Failed to save tier quota",
      adminUsersLoadFailed: "Failed to load users",
      adminPlanLoadFailed: "Failed to load plans",
      adminUserTierUpdated: "User tier updated",
      adminUserTierUpdateFailed: "Failed to update user tier",
      adminWaiting: "Waiting for operation",
      adminChooseTier: "Please choose a tier",
      adminSaveUserTier: "Save User Tier",
      adminMonthUsage: "This month Upload {upUsed}/{upLimit} · Synthesize {syUsed}/{syLimit}",
      adminIsAdmin: "Admin",
      docsEmpty: "No uploaded files",
      docsLoadFailed: "Failed to load file list",
      actionOpen: "Open",
      actionDeleteDoc: "Delete File",
      confirmDeleteDoc: "Delete this file?\n{filename}\n\nHistory audio will be kept.",
      docDeleted: "File deleted: {filename}",
    },
  },
  "ja-JP": {
    ui: {
      docTitle: "EPUB/PDF/TXT/Word 音声サーバー",
      accountTitle: "アカウント",
      languageLabel: "言語",
      usernamePlaceholder: "ユーザー名 (3-32文字)",
      passwordPlaceholder: "パスワード (6文字以上)",
      registerBtn: "登録",
      loginBtn: "ログイン",
      logoutBtn: "ログアウト",
      appTitle: "ドキュメント音声サーバー",
      appSubTitle: "ローカルまたはVPSで動作し、EPUB/PDF/TXT/WordをアップロードしてTTSエンジンで音声化します。",
      uploadBtn: "ドキュメントをアップロード",
      chapterPanelTitle: "章",
      textPanelTitle: "本文",
      ttsConfigTitle: "TTSエンジン設定",
      labelEngine: "エンジン",
      labelApiKey: "API Key",
      labelEndpoint: "Endpoint",
      labelModel: "Model",
      labelVoiceSelect: "Voice (自動リスト)",
      labelVoiceCustom: "Voice 手動上書き (任意)",
      labelSpeed: "Speed (0.25 - 4.0)",
      labelOutputFormat: "Output format",
      labelInstructions: "Instructions (OpenAI 任意)",
      labelCustomHeaders: "Custom headers JSON (Custom HTTPのみ)",
      apiKeyPlaceholder: "OpenAI/サードパーティ API Key",
      endpointPlaceholder: "任意。OpenAI既定: /v1/audio/speech",
      modelPlaceholder: "例: gpt-4o-mini-tts",
      voiceCustomPlaceholder: "空欄ならドロップダウンを使用",
      instructionsPlaceholder: "例: やさしく安定した口調で朗読",
      customHeadersPlaceholder: "{\"X-API-Key\":\"xxx\"}",
      synthesizeChapterBtn: "選択章を合成",
      synthesizeTextBtn: "テキスト欄を合成",
      chainStartBtn: "最後まで連続合成",
      chainStopBtn: "連続停止",
      saveProfileBtn: "設定を保存",
      loadProfileBtn: "設定を読み込み",
      prefetchNextLabel: "再生中に次章を先行合成",
      downloadLink: "音声をダウンロード",
      documentsTitle: "アップロード済みファイル",
      refreshDocsBtn: "ファイル一覧を更新",
      historyTitle: "履歴音声",
      refreshHistoryBtn: "履歴を更新",
      quotaStatusPrefix: "利用枠",
      adminTitle: "管理コンソール",
      adminPlansTitle: "プランごとの上限",
      adminUsersTitle: "ユーザー等級管理",
      adminSavePlanBtn: "プラン上限を保存",
      engineOpenai: "OpenAI TTS",
      engineEdge: "Edge TTS (無料)",
      engineCustom: "カスタム HTTP API",
    },
    msg: {
      notLoggedIn: "未ログイン",
      waitingUpload: "アップロード待機中",
      waitingSynthesis: "合成待機中",
      historyEmpty: "履歴音声はありません",
      loginFirst: "先にログインしてください",
      downloadFailed: "ダウンロード失敗",
      deleteFailed: "削除失敗",
      historyDeleted: "履歴音声を削除しました",
      historyLoadFailed: "履歴の読み込みに失敗しました",
      noVoicesManualInput: "利用可能な音声がありません。手動入力してください",
      sessionExpiredRelogin: "セッション期限切れです。再ログインしてください",
      loadVoicesFailed: "音声一覧の読み込みに失敗しました",
      loadProfileFailed: "設定の読み込みに失敗しました",
      pleaseLogin: "先にログインしてください",
      saveProfileFailed: "設定の保存に失敗しました",
      profileSavedUser: "設定を保存しました（{username}）",
      profileLoadedUser: "設定を読み込みました（{username}）",
      enterUserPass: "ユーザー名とパスワードを入力してください",
      authFailed: "認証に失敗しました",
      loggedInUser: "ログイン中: {username}",
      uploadPickFile: ".epub / .pdf / .txt / .docx を選択してください",
      uploadingParsing: "アップロードして解析中...",
      uploadFailed: "アップロード失敗",
      chapterOption: "[{index}] {title} ({length}文字)",
      loadedChapterCountFilename: "{count}章を読み込み: {filename}",
      loadChapterFailed: "章の読み込みに失敗しました",
      submitJobFailed: "ジョブ送信に失敗しました",
      audioFetchFailed: "音声の取得に失敗しました",
      queryJobFailed: "ジョブ状態の取得に失敗しました",
      queueWaitingPrefix: "{prefix}待機中。前のジョブの完了を待っています...",
      synthesizingProgressPrefix: "{prefix}合成中... {done}/{total} チャンク",
      synthFailed: "合成失敗",
      stoppingChain: "連続合成を停止中...",
      taskInProgress: "実行中のタスクがあります。しばらくお待ちください...",
      uploadAndChooseChapter: "先にドキュメントをアップロードして章を選択してください",
      chooseStartChapter: "開始章を選択してください",
      chapterPrefix: "{index}章: ",
      playingAndPrefetch: "{current}章を再生中、{next}章を先行合成中...",
      playingChapter: "{index}章を再生中...",
      reachedLastChapter: "最後の章まで連続合成・再生しました",
      chainStopped: "連続合成を停止しました",
      uploadOrInputPrompt: "先に EPUB/PDF/TXT/Word をアップロードするか本文を入力してください",
      submittingJob: "ジョブを送信中...",
      duplicateSynthDefault: "この章はすでに合成済みです",
      duplicateConfirm: "{tip}\n\nOKで再合成、キャンセルで既存音声を再生します。",
      replayExisting: "{tip}、既存音声を再生します...",
      synthDoneChunks: "合成完了、チャンク数: {chunks}",
      loggedOut: "ログアウトしました",
      customText: "カスタムテキスト",
      unnamedBook: "無題の書籍",
      chapterShort: "{index}章",
      chapterTitleWithBook: "{book} · {index}章{suffix}",
      chapterTitleNoBook: "{index}章{suffix}",
      confirmDelete: "この履歴音声を削除しますか？\n{title}",
      actionPlay: "再生",
      actionDownload: "ダウンロード",
      actionDelete: "削除",
      quotaLine: "利用枠: {tier} | アップロード {upUsed}/{upLimit} | 合成 {syUsed}/{syLimit}",
      unlimited: "無制限",
      adminPlanSaved: "プラン上限を保存しました",
      adminPlanSaveFailed: "プラン上限の保存に失敗しました",
      adminUsersLoadFailed: "ユーザー一覧の取得に失敗しました",
      adminPlanLoadFailed: "プラン一覧の取得に失敗しました",
      adminUserTierUpdated: "ユーザー等級を更新しました",
      adminUserTierUpdateFailed: "ユーザー等級の更新に失敗しました",
      adminWaiting: "操作待機中",
      adminChooseTier: "等級を選択してください",
      adminSaveUserTier: "ユーザー等級を保存",
      adminMonthUsage: "今月 アップロード {upUsed}/{upLimit} ・ 合成 {syUsed}/{syLimit}",
      adminIsAdmin: "管理者",
      docsEmpty: "アップロード済みファイルはありません",
      docsLoadFailed: "ファイル一覧の取得に失敗しました",
      actionOpen: "開く",
      actionDeleteDoc: "ファイル削除",
      confirmDeleteDoc: "このファイルを削除しますか？\n{filename}\n\n履歴音声は保持されます。",
      docDeleted: "ファイルを削除しました: {filename}",
    },
  },
};

const SUPPORTED_LANGS = ["zh-CN", "zh-TW", "en-US", "ja-JP"];
let currentLang = "zh-CN";

function getNestedText(obj, key) {
  return key.split(".").reduce((acc, part) => (acc && acc[part] !== undefined ? acc[part] : undefined), obj);
}

function formatText(template, vars = {}) {
  return String(template).replace(/\{(\w+)\}/g, (_m, name) => (vars[name] !== undefined ? String(vars[name]) : ""));
}

function t(key, vars = {}) {
  const langPack = I18N[currentLang] || I18N["zh-CN"];
  const fallbackPack = I18N["zh-CN"];
  const raw = getNestedText(langPack, key) ?? getNestedText(fallbackPack, key) ?? key;
  return formatText(raw, vars);
}

function normalizeLanguage(raw) {
  const value = String(raw || "").trim();
  if (SUPPORTED_LANGS.includes(value)) return value;
  const lower = value.toLowerCase();
  if (lower.startsWith("zh-tw") || lower.startsWith("zh-hk") || lower.startsWith("zh-mo")) return "zh-TW";
  if (lower.startsWith("zh")) return "zh-CN";
  if (lower.startsWith("ja")) return "ja-JP";
  if (lower.startsWith("en")) return "en-US";
  return "zh-CN";
}

function applyLanguageToUI() {
  document.documentElement.lang = currentLang;
  document.title = t("ui.docTitle");

  const setText = (id, key, vars = {}) => {
    const el = document.getElementById(id);
    if (el) el.textContent = t(key, vars);
  };
  const setPlaceholder = (id, key) => {
    const el = document.getElementById(id);
    if (el) el.placeholder = t(key);
  };

  setText("accountTitle", "ui.accountTitle");
  setText("languageLabel", "ui.languageLabel");
  setText("registerBtn", "ui.registerBtn");
  setText("loginBtn", "ui.loginBtn");
  setText("logoutBtn", "ui.logoutBtn");
  setText("appTitle", "ui.appTitle");
  setText("appSubTitle", "ui.appSubTitle");
  setText("uploadBtn", "ui.uploadBtn");
  setText("chapterPanelTitle", "ui.chapterPanelTitle");
  setText("textPanelTitle", "ui.textPanelTitle");
  setText("ttsConfigTitle", "ui.ttsConfigTitle");
  setText("labelEngine", "ui.labelEngine");
  setText("labelApiKey", "ui.labelApiKey");
  setText("labelEndpoint", "ui.labelEndpoint");
  setText("labelModel", "ui.labelModel");
  setText("labelVoiceSelect", "ui.labelVoiceSelect");
  setText("labelVoiceCustom", "ui.labelVoiceCustom");
  setText("labelSpeed", "ui.labelSpeed");
  setText("labelOutputFormat", "ui.labelOutputFormat");
  setText("labelInstructions", "ui.labelInstructions");
  setText("labelCustomHeaders", "ui.labelCustomHeaders");
  setText("synthesizeChapterBtn", "ui.synthesizeChapterBtn");
  setText("synthesizeTextBtn", "ui.synthesizeTextBtn");
  setText("chainStartBtn", "ui.chainStartBtn");
  setText("chainStopBtn", "ui.chainStopBtn");
  setText("saveProfileBtn", "ui.saveProfileBtn");
  setText("loadProfileBtn", "ui.loadProfileBtn");
  setText("prefetchNextLabel", "ui.prefetchNextLabel");
  setText("downloadLink", "ui.downloadLink");
  setText("documentsTitle", "ui.documentsTitle");
  setText("refreshDocsBtn", "ui.refreshDocsBtn");
  setText("historyTitle", "ui.historyTitle");
  setText("refreshHistoryBtn", "ui.refreshHistoryBtn");
  setText("adminTitle", "ui.adminTitle");
  setText("adminPlansTitle", "ui.adminPlansTitle");
  setText("adminUsersTitle", "ui.adminUsersTitle");
  setText("adminSavePlanBtn", "ui.adminSavePlanBtn");

  setPlaceholder("authUsername", "ui.usernamePlaceholder");
  setPlaceholder("authPassword", "ui.passwordPlaceholder");
  setPlaceholder("apiKey", "ui.apiKeyPlaceholder");
  setPlaceholder("endpoint", "ui.endpointPlaceholder");
  setPlaceholder("model", "ui.modelPlaceholder");
  setPlaceholder("voiceCustom", "ui.voiceCustomPlaceholder");
  setPlaceholder("instructions", "ui.instructionsPlaceholder");
  setPlaceholder("customHeaders", "ui.customHeadersPlaceholder");

  Array.from(engine.options).forEach((opt) => {
    if (opt.value === "openai") opt.textContent = t("ui.engineOpenai");
    if (opt.value === "edge_tts") opt.textContent = t("ui.engineEdge");
    if (opt.value === "custom_http") opt.textContent = t("ui.engineCustom");
  });

  if (adminPlanStatus && !currentUserIsAdmin) {
    setAdminPlanStatus(t("msg.adminWaiting"));
  }
}

function setCookie(name, value, days = 365) {
  const maxAge = Math.max(1, Math.floor(days * 24 * 60 * 60));
  document.cookie = `${encodeURIComponent(name)}=${encodeURIComponent(value)}; Path=/; Max-Age=${maxAge}; SameSite=Lax`;
}

function getCookie(name) {
  const key = `${encodeURIComponent(name)}=`;
  const parts = document.cookie ? document.cookie.split("; ") : [];
  for (const p of parts) {
    if (p.startsWith(key)) return decodeURIComponent(p.slice(key.length));
  }
  return "";
}

function saveLanguageToLocalStorage() {
  setCookie("epub_tts_lang", currentLang, 365);
}

function loadLanguageFromLocalStorage() {
  const stored = getCookie("epub_tts_lang");
  const browser = navigator.language || "zh-CN";
  currentLang = normalizeLanguage(stored || browser);
}

function setAuthStatus(text, isError = false) {
  authStatus.textContent = text;
  authStatus.classList.toggle("error", isError);
}

function setUploadStatus(text, isError = false) {
  uploadStatus.textContent = text;
  uploadStatus.classList.toggle("error", isError);
}

function setTtsStatus(text, isError = false) {
  ttsStatus.textContent = text;
  ttsStatus.classList.toggle("error", isError);
}

function setAdminPlanStatus(text, isError = false) {
  if (!adminPlanStatus) return;
  adminPlanStatus.textContent = text;
  adminPlanStatus.classList.toggle("error", isError);
}

function formatLimitValue(limit) {
  return Number(limit) < 0 ? t("msg.unlimited") : String(limit);
}

function renderQuotaStatus(quota) {
  if (!quota) {
    quotaStatus.textContent = `${t("ui.quotaStatusPrefix")}: -`;
    quotaStatus.classList.remove("error");
    return;
  }
  quotaStatus.textContent = t("msg.quotaLine", {
    tier: quota.tier_display_name || quota.tier || "-",
    upUsed: quota.usage?.uploads_month ?? 0,
    upLimit: formatLimitValue(quota.limits?.uploads_month ?? -1),
    syUsed: quota.usage?.syntheses_month ?? 0,
    syLimit: formatLimitValue(quota.limits?.syntheses_month ?? -1),
  });
  quotaStatus.classList.remove("error");
}

async function loadQuotaStatus() {
  const { resp, data } = await apiJson("/api/quota");
  if (!resp.ok) {
    quotaStatus.textContent = data.detail || t("msg.historyLoadFailed");
    quotaStatus.classList.add("error");
    return null;
  }
  renderQuotaStatus(data);
  return data;
}

function setAdminPanelVisible(visible) {
  if (!adminPanel) return;
  adminPanel.hidden = !visible;
}

function setProgress(percent) {
  const safe = Math.max(0, Math.min(100, Number(percent || 0)));
  ttsProgress.value = safe;
  ttsProgressText.textContent = `${Math.round(safe)}%`;
}

function setDownloadDisabled(disabled) {
  if (disabled) {
    downloadLink.classList.add("disabled");
    downloadLink.removeAttribute("href");
    downloadLink.removeAttribute("download");
  } else {
    downloadLink.classList.remove("disabled");
  }
}

function formatDateTime(isoText) {
  if (!isoText) return "";
  const dt = new Date(isoText);
  if (Number.isNaN(dt.getTime())) return isoText;
  return dt.toLocaleString(currentLang);
}

function formatChapterTitle(index, chapterTitle, bookTitle) {
  const suffix = chapterTitle ? ` - ${chapterTitle}` : "";
  if (bookTitle) {
    return t("msg.chapterTitleWithBook", { book: bookTitle, index: index + 1, suffix });
  }
  return t("msg.chapterTitleNoBook", { index: index + 1, suffix });
}

function formatChapterPrefix(index) {
  return t("msg.chapterPrefix", { index: index + 1 });
}

function setLanguage(lang, refreshHistory = true) {
  currentLang = normalizeLanguage(lang);
  if (languageSelect) {
    languageSelect.value = currentLang;
  }
  saveLanguageToLocalStorage();
  applyLanguageToUI();
  if (refreshHistory) {
    loadDocumentsList().catch(() => {});
    loadHistoryList().catch(() => {});
    loadQuotaStatus().catch(() => {});
  }
}

function bindDocumentsRefreshButton() {
  if (!refreshDocsBtn || docsRefreshBound) return;
  refreshDocsBtn.addEventListener("click", loadDocumentsList);
  docsRefreshBound = true;
}

function ensureDocumentsSection() {
  if (documentsList && refreshDocsBtn) {
    bindDocumentsRefreshButton();
    return;
  }
  const uploadCard = document.querySelector(".upload-card");
  if (!uploadCard) return;

  let titleEl = document.getElementById("documentsTitle");
  let listEl = document.getElementById("documentsList");
  let refreshEl = document.getElementById("refreshDocsBtn");
  const uploadStatusEl = document.getElementById("uploadStatus");

  if (!titleEl || !listEl) {
    const head = document.createElement("div");
    head.className = "history-head";

    if (!titleEl) {
      titleEl = document.createElement("h3");
      titleEl.id = "documentsTitle";
    }
    head.appendChild(titleEl);

    if (!refreshEl) {
      refreshEl = document.createElement("button");
      refreshEl.id = "refreshDocsBtn";
    }
    head.appendChild(refreshEl);

    if (!listEl) {
      listEl = document.createElement("div");
      listEl.id = "documentsList";
      listEl.className = "history-list";
    }

    if (uploadStatusEl && uploadStatusEl.parentElement === uploadCard) {
      uploadStatusEl.insertAdjacentElement("afterend", head);
      head.insertAdjacentElement("afterend", listEl);
    } else {
      uploadCard.appendChild(head);
      uploadCard.appendChild(listEl);
    }
  }

  refreshDocsBtn = refreshEl;
  documentsList = listEl;
  bindDocumentsRefreshButton();
}

function clearDocumentsList(text = t("msg.docsEmpty")) {
  if (!documentsList) return;
  documentsList.innerHTML = "";
  const item = document.createElement("div");
  item.className = "history-item";
  const meta = document.createElement("div");
  meta.className = "history-meta";
  meta.textContent = text;
  item.appendChild(meta);
  documentsList.appendChild(item);
}

function applyDocumentData(data) {
  currentDocId = data.doc_id;
  currentChapters = data.chapters || [];
  chapterSelect.innerHTML = "";
  currentChapters.forEach((ch) => {
    const option = document.createElement("option");
    option.value = String(ch.index);
    option.textContent = t("msg.chapterOption", { index: ch.index, title: ch.title, length: ch.length });
    chapterSelect.appendChild(option);
  });
}

async function openDocument(docId) {
  const { resp, data } = await apiJson(`/api/documents/${docId}`);
  if (!resp.ok) {
    setUploadStatus(data.detail || t("msg.docsLoadFailed"), true);
    return;
  }
  applyDocumentData(data);
  if (currentChapters.length > 0) {
    chapterSelect.selectedIndex = 0;
    await loadChapterText(0);
  } else {
    chapterText.value = "";
  }
  setUploadStatus(t("msg.loadedChapterCountFilename", { count: data.chapter_count, filename: data.filename }));
  updateActionButtons();
}

async function deleteDocumentItem(doc) {
  const ok = window.confirm(t("msg.confirmDeleteDoc", { filename: doc.filename || doc.doc_id }));
  if (!ok) return;
  const { resp, data } = await apiJson(`/api/documents/${doc.doc_id}`, { method: "DELETE" });
  if (!resp.ok) {
    throw new Error(data.detail || t("msg.deleteFailed"));
  }
  if (currentDocId === doc.doc_id) {
    currentDocId = null;
    currentChapters = [];
    chapterSelect.innerHTML = "";
    chapterText.value = "";
    clearAudio();
  }
  updateActionButtons();
}

function renderDocumentsList(docs) {
  if (!documentsList) return;
  documentsList.innerHTML = "";
  if (!docs || docs.length === 0) {
    clearDocumentsList(t("msg.docsEmpty"));
    return;
  }
  docs.forEach((doc) => {
    const item = document.createElement("div");
    item.className = "history-item";
    if (currentDocId === doc.doc_id) {
      item.classList.add("active-doc");
    }
    const left = document.createElement("div");
    const title = document.createElement("div");
    title.className = "history-title";
    title.textContent = doc.filename || doc.doc_id;
    const meta = document.createElement("div");
    meta.className = "history-meta";
    meta.textContent = `${doc.chapter_count ?? 0} · ${formatDateTime(doc.created_at)}`;
    left.appendChild(title);
    left.appendChild(meta);

    const right = document.createElement("div");
    right.className = "history-actions";
    const openBtn = document.createElement("button");
    openBtn.textContent = t("msg.actionOpen");
    openBtn.addEventListener("click", async () => {
      try {
        await openDocument(doc.doc_id);
        await loadDocumentsList();
      } catch (err) {
        setUploadStatus(String(err.message || err), true);
      }
    });
    const delBtn = document.createElement("button");
    delBtn.textContent = t("msg.actionDeleteDoc");
    delBtn.className = "danger";
    delBtn.addEventListener("click", async () => {
      try {
        await deleteDocumentItem(doc);
        await loadDocumentsList();
        await loadHistoryList();
        setUploadStatus(t("msg.docDeleted", { filename: doc.filename || doc.doc_id }));
      } catch (err) {
        setUploadStatus(String(err.message || err), true);
      }
    });
    right.appendChild(openBtn);
    right.appendChild(delBtn);
    item.appendChild(left);
    item.appendChild(right);
    documentsList.appendChild(item);
  });
}

async function loadDocumentsList() {
  if (!documentsList) {
    ensureDocumentsSection();
  }
  if (!documentsList) return;
  const { resp, data } = await apiJson("/api/documents?limit=200");
  if (!resp.ok) {
    clearDocumentsList(data.detail || t("msg.docsLoadFailed"));
    return;
  }
  renderDocumentsList(data.documents || []);
}

function clearHistoryList(text = t("msg.historyEmpty")) {
  historyList.innerHTML = "";
  const item = document.createElement("div");
  item.className = "history-item";
  item.innerHTML = `<div class="history-meta">${text}</div>`;
  historyList.appendChild(item);
}

async function downloadJobAudio(jobId) {
  const resp = await apiFetch(`/api/synthesize_jobs/${jobId}/download`);
  if (!resp.ok) {
    let detail = t("msg.downloadFailed");
    try {
      const data = await resp.json();
      detail = data.detail || detail;
    } catch (_err) {
    }
    throw new Error(detail);
  }
  const blob = await resp.blob();
  const filename = parseFilenameFromDisposition(resp.headers.get("Content-Disposition")) || `tts_${jobId.slice(0, 8)}.mp3`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 3000);
}

async function deleteJobAudio(job) {
  const title = job.source_type === "chapter"
    ? `${job.source_book_title || t("msg.unnamedBook")} / ${job.source_chapter_title || t("msg.chapterShort", { index: (job.source_chapter_index ?? 0) + 1 })}`
    : t("msg.customText");
  const ok = window.confirm(t("msg.confirmDelete", { title }));
  if (!ok) return;

  const resp = await apiFetch(`/api/synthesize_jobs/${job.job_id}`, { method: "DELETE" });
  if (!resp.ok) {
    let detail = t("msg.deleteFailed");
    try {
      const data = await resp.json();
      detail = data.detail || detail;
    } catch (_err) {
    }
    throw new Error(detail);
  }

  if (currentPlayingJobId === job.job_id) {
    clearAudio();
  }
}

function renderHistoryList(jobs) {
  historyList.innerHTML = "";
  if (!jobs || jobs.length === 0) {
    clearHistoryList(t("msg.historyEmpty"));
    return;
  }

  jobs.forEach((job) => {
    const item = document.createElement("div");
    item.className = "history-item";

    let title = "";
    if (job.source_type === "chapter") {
      const idx = job.source_chapter_index ?? 0;
      title = formatChapterTitle(idx, job.source_chapter_title || "", job.source_book_title || "");
    } else {
      title = t("msg.customText");
    }

    const left = document.createElement("div");
    const titleEl = document.createElement("div");
    titleEl.className = "history-title";
    titleEl.textContent = title;
    const metaEl = document.createElement("div");
    metaEl.className = "history-meta";
    metaEl.textContent = `${job.engine} · ${job.output_format} · ${formatDateTime(job.updated_at)} · ${job.status}`;
    left.appendChild(titleEl);
    left.appendChild(metaEl);

    const right = document.createElement("div");
    right.className = "history-actions";

    const playBtn = document.createElement("button");
    playBtn.textContent = t("msg.actionPlay");
    playBtn.disabled = job.status !== "completed";
    playBtn.addEventListener("click", async () => {
      try {
        await fetchAndPlayAudio(job.job_id);
      } catch (err) {
        setTtsStatus(String(err.message || err), true);
      }
    });

    const dlBtn = document.createElement("button");
    dlBtn.textContent = t("msg.actionDownload");
    dlBtn.disabled = job.status !== "completed";
    dlBtn.addEventListener("click", async () => {
      try {
        await downloadJobAudio(job.job_id);
      } catch (err) {
        setTtsStatus(String(err.message || err), true);
      }
    });

    const delBtn = document.createElement("button");
    delBtn.textContent = t("msg.actionDelete");
    delBtn.className = "danger";
    delBtn.addEventListener("click", async () => {
      try {
        await deleteJobAudio(job);
        await loadHistoryList();
        setTtsStatus(t("msg.historyDeleted"));
      } catch (err) {
        setTtsStatus(String(err.message || err), true);
      }
    });

    right.appendChild(playBtn);
    right.appendChild(dlBtn);
    right.appendChild(delBtn);
    item.appendChild(left);
    item.appendChild(right);
    historyList.appendChild(item);
  });
}

async function loadHistoryList() {
  const { resp, data } = await apiJson("/api/synthesize_jobs?completed_only=true&limit=100");
  if (!resp.ok) {
    clearHistoryList(data.detail || t("msg.historyLoadFailed"));
    return;
  }
  renderHistoryList(data.jobs || []);
}

function createTierSelect(plans, selectedTier) {
  const select = document.createElement("select");
  const first = document.createElement("option");
  first.value = "";
  first.textContent = t("msg.adminChooseTier");
  select.appendChild(first);
  (plans || []).forEach((p) => {
    const opt = document.createElement("option");
    opt.value = p.tier;
    opt.textContent = `${p.display_name} (${p.tier})`;
    select.appendChild(opt);
  });
  if (selectedTier) select.value = selectedTier;
  return select;
}

function renderAdminUsers(usersData, plans) {
  if (!adminUsersList) return;
  adminUsersList.innerHTML = "";
  if (!usersData || usersData.length === 0) {
    const item = document.createElement("div");
    item.className = "admin-user-item";
    item.textContent = t("msg.historyEmpty");
    adminUsersList.appendChild(item);
    return;
  }
  usersData.forEach((u) => {
    const item = document.createElement("div");
    item.className = "admin-user-item";

    const head = document.createElement("div");
    head.className = "admin-user-head";
    head.innerHTML = `<span class="admin-user-name">${u.username}</span><span class="admin-user-meta">${u.is_admin ? t("msg.adminIsAdmin") : ""}</span>`;

    const usage = document.createElement("div");
    usage.className = "admin-user-meta";
    usage.textContent = t("msg.adminMonthUsage", {
      upUsed: u.usage?.uploads_month ?? 0,
      upLimit: formatLimitValue(u.limits?.uploads_month ?? -1),
      syUsed: u.usage?.syntheses_month ?? 0,
      syLimit: formatLimitValue(u.limits?.syntheses_month ?? -1),
    });

    const controls = document.createElement("div");
    controls.className = "admin-user-controls";
    const tierSel = createTierSelect(plans, u.tier);
    const saveBtn = document.createElement("button");
    saveBtn.textContent = t("msg.adminSaveUserTier");
    saveBtn.addEventListener("click", async () => {
      try {
        const tier = (tierSel.value || "").trim();
        if (!tier) {
          setAdminPlanStatus(t("msg.adminChooseTier"), true);
          return;
        }
        const { resp, data } = await apiJson(`/api/admin/users/${encodeURIComponent(u.username)}/tier`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ tier }),
        });
        if (!resp.ok) {
          setAdminPlanStatus(data.detail || t("msg.adminUserTierUpdateFailed"), true);
          return;
        }
        setAdminPlanStatus(t("msg.adminUserTierUpdated"));
        await loadAdminConsole();
        await loadQuotaStatus();
      } catch (err) {
        setAdminPlanStatus(String(err.message || err), true);
      }
    });
    controls.appendChild(tierSel);
    controls.appendChild(saveBtn);

    item.appendChild(head);
    item.appendChild(usage);
    item.appendChild(controls);
    adminUsersList.appendChild(item);
  });
}

function fillPlanInputs(plans, tier) {
  const plan = (plans || []).find((p) => p.tier === tier);
  if (!plan) return;
  adminPlanUploads.value = String(plan.max_uploads_month);
  adminPlanSynths.value = String(plan.max_syntheses_month);
}

async function loadAdminConsole() {
  if (!authToken || !currentUserIsAdmin) {
    setAdminPanelVisible(false);
    return;
  }
  setAdminPanelVisible(true);
  setAdminPlanStatus(t("msg.adminWaiting"));

  const [{ resp: planResp, data: planData }, { resp: userResp, data: userData }] = await Promise.all([
    apiJson("/api/admin/plans"),
    apiJson("/api/admin/users"),
  ]);
  if (!planResp.ok) {
    setAdminPlanStatus(planData.detail || t("msg.adminPlanLoadFailed"), true);
    return;
  }
  if (!userResp.ok) {
    setAdminPlanStatus(userData.detail || t("msg.adminUsersLoadFailed"), true);
    return;
  }

  const plans = planData.plans || [];
  adminPlanSelect.innerHTML = "";
  plans.forEach((p) => {
    const opt = document.createElement("option");
    opt.value = p.tier;
    opt.textContent = `${p.display_name} (${p.tier})`;
    adminPlanSelect.appendChild(opt);
  });
  if (plans.length > 0) {
    adminPlanSelect.value = plans[0].tier;
    fillPlanInputs(plans, plans[0].tier);
  }
  adminPlanSelect.onchange = () => fillPlanInputs(plans, adminPlanSelect.value);
  renderAdminUsers(userData.users || [], plans);
}

async function saveAdminPlan() {
  if (!authToken || !currentUserIsAdmin) return;
  const tier = (adminPlanSelect.value || "").trim();
  if (!tier) {
    setAdminPlanStatus(t("msg.adminChooseTier"), true);
    return;
  }
  const max_uploads_month = Number(adminPlanUploads.value);
  const max_syntheses_month = Number(adminPlanSynths.value);
  const { resp, data } = await apiJson(`/api/admin/plans/${encodeURIComponent(tier)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ max_uploads_month, max_syntheses_month }),
  });
  if (!resp.ok) {
    setAdminPlanStatus(data.detail || t("msg.adminPlanSaveFailed"), true);
    return;
  }
  setAdminPlanStatus(t("msg.adminPlanSaved"));
  await loadAdminConsole();
  await loadQuotaStatus();
}

function updateActionButtons() {
  const baseReady = appEnabled && !synthesisInProgress && !chainRunning;
  synthesizeChapterBtn.disabled = !baseReady;
  synthesizeTextBtn.disabled = !baseReady;
  chainStartBtn.disabled = !baseReady || !currentDocId;
  chainStopBtn.disabled = !chainRunning;
  prefetchNextToggle.disabled = !appEnabled || chainRunning;
}

function setAppEnabled(enabled) {
  appEnabled = enabled;
  [
    epubFile,
    uploadBtn,
    refreshDocsBtn,
    chapterSelect,
    chapterText,
    engine,
    apiKey,
    endpoint,
    model,
    voiceSelect,
    voiceCustom,
    speed,
    outputFormat,
    instructions,
    customHeaders,
    saveProfileBtn,
    loadProfileBtn,
    refreshHistoryBtn,
    adminPlanSelect,
    adminPlanUploads,
    adminPlanSynths,
    adminSavePlanBtn,
  ].forEach((el) => {
    if (el) {
      el.disabled = !enabled;
    }
  });
  if (!enabled) {
    setDownloadDisabled(true);
    clearHistoryList(t("msg.historyEmpty"));
    renderQuotaStatus(null);
    setAdminPanelVisible(false);
  }
  updateActionButtons();
}

function clearAudio() {
  if (currentAudioUrl) {
    URL.revokeObjectURL(currentAudioUrl);
    currentAudioUrl = null;
  }
  currentPlayingJobId = "";
  player.removeAttribute("src");
  setDownloadDisabled(true);
}

function getSelectedChapterIndex() {
  if (chapterSelect.selectedIndex < 0) return null;
  return Number(chapterSelect.value);
}

function getVoiceValue() {
  const custom = (voiceCustom.value || "").trim();
  if (custom) return custom;
  return voiceSelect.value || null;
}

function parseFilenameFromDisposition(contentDisposition) {
  if (!contentDisposition) return "";
  const utf8 = contentDisposition.match(/filename\*\s*=\s*UTF-8''([^;]+)/i);
  if (utf8 && utf8[1]) {
    try {
      return decodeURIComponent(utf8[1]);
    } catch (_err) {
    }
  }
  const m = contentDisposition.match(/filename=\"([^\"]+)\"/i);
  return m && m[1] ? m[1] : "";
}

function setVoiceOptions(voices, preferredVoice) {
  voiceSelect.innerHTML = "";
  if (!voices || voices.length === 0) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = t("msg.noVoicesManualInput");
    voiceSelect.appendChild(option);
    voiceSelect.value = "";
    return;
  }
  voices.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.id;
    const tags = [item.locale, item.gender].filter(Boolean).join(" / ");
    option.textContent = tags ? `${item.name} (${tags})` : item.name;
    voiceSelect.appendChild(option);
  });

  if (preferredVoice && voices.some((v) => v.id === preferredVoice)) {
    voiceSelect.value = preferredVoice;
  } else {
    voiceSelect.selectedIndex = 0;
  }
}

async function apiFetch(url, options = {}) {
  const headers = new Headers(options.headers || {});
  if (authToken && authToken !== GUEST_TOKEN) {
    headers.set("Authorization", `Bearer ${authToken}`);
  }
  const finalOptions = { ...options, headers };
  return fetch(url, finalOptions);
}

async function apiJson(url, options = {}) {
  const resp = await apiFetch(url, options);
  let data = {};
  try {
    data = await resp.json();
  } catch (_err) {
    data = {};
  }
  return { resp, data };
}

function saveAuthToLocalStorage() {
  authToken = GUEST_TOKEN;
  currentUsername = "local";
  currentUserTier = "local";
  currentUserIsAdmin = false;
}

function loadAuthFromLocalStorage() {
  authToken = GUEST_TOKEN;
  currentUsername = "local";
  currentUserTier = "local";
  currentUserIsAdmin = false;
}

function clearAuthState() {
  authToken = GUEST_TOKEN;
  currentUsername = "local";
  currentUserTier = "local";
  currentUserIsAdmin = false;
}

function saveConfigToLocalStorage() {
  const data = {
    engine: engine.value,
    apiKey: apiKey.value,
    endpoint: endpoint.value,
    model: model.value,
    voiceSelect: voiceSelect.value,
    voiceCustom: voiceCustom.value,
    speed: speed.value,
    outputFormat: outputFormat.value,
    instructions: instructions.value,
    customHeaders: customHeaders.value,
    prefetchNext: prefetchNextToggle.checked,
  };
  setCookie("epub_tts_server_config", JSON.stringify(data), 365);
}

function loadConfigFromLocalStorage() {
  try {
    const raw = getCookie("epub_tts_server_config");
    if (!raw) return;
    const data = JSON.parse(raw);
    engine.value = data.engine || "openai";
    apiKey.value = data.apiKey || "";
    endpoint.value = data.endpoint || "";
    model.value = data.model || "";
    voiceCustom.value = data.voiceCustom || "";
    speed.value = data.speed || "1.0";
    outputFormat.value = data.outputFormat || "mp3";
    instructions.value = data.instructions || "";
    customHeaders.value = data.customHeaders || "";
    prefetchNextToggle.checked = data.prefetchNext !== false;
    voiceSelect.dataset.preferred = data.voiceSelect || "";
  } catch (_err) {
  }
}

function collectEngineConfig() {
  return {
    api_key: apiKey.value || "",
    endpoint: endpoint.value || "",
    model: model.value || "",
    voice: getVoiceValue() || "",
    instructions: instructions.value || "",
    custom_headers_json: customHeaders.value || "",
    speed: Number(speed.value || 1),
    output_format: outputFormat.value || "mp3",
  };
}

function applyEngineConfig(config) {
  const cfg = config || {};
  apiKey.value = cfg.api_key || "";
  endpoint.value = cfg.endpoint || "";
  model.value = cfg.model || "";
  voiceCustom.value = cfg.voice || "";
  instructions.value = cfg.instructions || "";
  customHeaders.value = cfg.custom_headers_json || "";
  speed.value = String(cfg.speed ?? "1.0");
  outputFormat.value = cfg.output_format || "mp3";
}

function applyEngineDefaults() {
  if (engine.value === "openai") {
    if (!model.value) model.value = "gpt-4o-mini-tts";
    if (!outputFormat.value) outputFormat.value = "mp3";
  } else if (engine.value === "edge_tts") {
    outputFormat.value = "mp3";
  }
}

async function loadVoicesForEngine() {
  const preferredVoice = (voiceCustom.value || "").trim() || voiceSelect.value || "";
  const { resp, data } = await apiJson(`/api/voices?engine=${encodeURIComponent(engine.value)}`);
  if (!resp.ok) {
    setVoiceOptions([], "");
    setTtsStatus(data.detail || t("msg.loadVoicesFailed"), true);
    return;
  }
  setVoiceOptions(data.voices || [], preferredVoice);
}

async function applyVoiceDefaults() {
  await loadVoicesForEngine();
  const preferred = voiceSelect.dataset.preferred || "";
  if (preferred) {
    voiceSelect.value = preferred;
    delete voiceSelect.dataset.preferred;
  }
  if (!voiceCustom.value.trim()) {
    if (engine.value === "openai" && (!voiceSelect.value || voiceSelect.value === "")) {
      voiceSelect.value = "alloy";
    } else if (engine.value === "edge_tts" && (!voiceSelect.value || voiceSelect.value === "")) {
      voiceSelect.value = "zh-CN-XiaoxiaoNeural";
    }
  }
}

async function loadProfileConfig(applyCurrentEngine = true) {
  try {
    const raw = getCookie("epub_tts_profile_configs");
    profileConfigs = raw ? JSON.parse(raw) : {};
  } catch (_err) {
    profileConfigs = {};
  }
  if (applyCurrentEngine) {
    applyEngineConfig(profileConfigs[engine.value] || {});
    applyEngineDefaults();
    await applyVoiceDefaults();
  }
}

async function saveProfileConfig() {
  profileConfigs[engine.value] = collectEngineConfig();
  setCookie("epub_tts_profile_configs", JSON.stringify(profileConfigs), 365);
  setAuthStatus(t("msg.profileSavedUser", { username: currentUsername }));
}

async function authAction(path) {
  const username = (authUsername.value || "").trim();
  const password = authPassword.value || "";
  if (!username || !password) {
    setAuthStatus(t("msg.enterUserPass"), true);
    return;
  }
  const { resp, data } = await apiJson(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!resp.ok) {
    setAuthStatus(data.detail || t("msg.authFailed"), true);
    return;
  }
  authToken = data.token || "";
  currentUsername = data.username || username;
  currentUserTier = data.tier || "free";
  currentUserIsAdmin = !!data.is_admin;
  saveAuthToLocalStorage();
  setAuthStatus(t("msg.loggedInUser", { username: currentUsername }));
  setAppEnabled(true);
  await loadProfileConfig(true);
  await loadQuotaStatus();
  await loadHistoryList();
  await loadAdminConsole();
  updateActionButtons();
}

async function verifySession() {
  if (!authToken) {
    setAppEnabled(false);
    setAuthStatus(t("msg.notLoggedIn"));
    return false;
  }
  const { resp, data } = await apiJson("/api/auth/me");
  if (!resp.ok) {
    clearAuthState();
    setAppEnabled(false);
    setAuthStatus(t("msg.sessionExpiredRelogin"), true);
    return false;
  }
  currentUsername = data.username || currentUsername;
  currentUserTier = data.tier || currentUserTier || "free";
  currentUserIsAdmin = !!data.is_admin;
  saveAuthToLocalStorage();
  setAuthStatus(t("msg.loggedInUser", { username: currentUsername }));
  setAppEnabled(true);
  await loadProfileConfig(true);
  await loadQuotaStatus();
  await loadHistoryList();
  await loadAdminConsole();
  updateActionButtons();
  return true;
}

async function uploadEpub() {
  const file = epubFile.files && epubFile.files[0];
  if (!file) {
    setUploadStatus(t("msg.uploadPickFile"), true);
    return;
  }
  clearAudio();
  setUploadStatus(t("msg.uploadingParsing"));

  const formData = new FormData();
  formData.append("file", file);
  const { resp, data } = await apiJson("/api/upload_epub", { method: "POST", body: formData });
  if (!resp.ok) {
    setUploadStatus(data.detail || t("msg.uploadFailed"), true);
    return;
  }

  applyDocumentData(data);
  if (currentChapters.length > 0) {
    chapterSelect.selectedIndex = 0;
    await loadChapterText(0);
  } else {
    chapterText.value = "";
  }
  setUploadStatus(t("msg.loadedChapterCountFilename", { count: data.chapter_count, filename: data.filename }));
  await loadQuotaStatus();
  await loadDocumentsList();
  updateActionButtons();
}

async function loadChapterText(index) {
  if (!currentDocId) return;
  const { resp, data } = await apiJson(`/api/documents/${currentDocId}/chapters/${index}`);
  if (!resp.ok) {
    setUploadStatus(data.detail || t("msg.loadChapterFailed"), true);
    return;
  }
  chapterText.value = data.text || "";
}

function buildSynthesisPayload(useCustomText, chapterIndexOverride = null) {
  const index = chapterIndexOverride === null ? getSelectedChapterIndex() : chapterIndexOverride;
  return {
    engine: engine.value,
    doc_id: currentDocId,
    chapter_index: index,
    custom_text: useCustomText ? chapterText.value : null,
    api_key: apiKey.value || null,
    endpoint: endpoint.value || null,
    model: model.value || null,
    voice: getVoiceValue(),
    speed: Number(speed.value || 1),
    output_format: outputFormat.value || "mp3",
    instructions: instructions.value || null,
    custom_headers_json: customHeaders.value || null,
  };
}

async function createSynthesisJob(payload, forceResynthesize = false) {
  const body = { ...payload, force_resynthesize: !!forceResynthesize };
  const { resp, data } = await apiJson("/api/synthesize_jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    throw new Error(data.detail || t("msg.submitJobFailed"));
  }
  if (!data.already_exists) {
    loadQuotaStatus().catch(() => {});
  }
  return {
    jobId: data.job_id,
    alreadyExists: !!data.already_exists,
    message: data.message || "",
  };
}

async function fetchAndPlayAudio(jobId) {
  const audioResp = await apiFetch(`/api/synthesize_jobs/${jobId}/audio`);
  if (!audioResp.ok) {
    let detail = t("msg.audioFetchFailed");
    try {
      const data = await audioResp.json();
      detail = data.detail || detail;
    } catch (_err) {
    }
    throw new Error(detail);
  }

  const blob = await audioResp.blob();
  const filename = parseFilenameFromDisposition(audioResp.headers.get("Content-Disposition")) || `tts_${jobId.slice(0, 8)}.mp3`;
  if (currentAudioUrl) {
    URL.revokeObjectURL(currentAudioUrl);
  }
  currentAudioUrl = URL.createObjectURL(blob);
  currentPlayingJobId = jobId;
  player.src = currentAudioUrl;
  downloadLink.href = currentAudioUrl;
  downloadLink.download = filename;
  setDownloadDisabled(false);
  await player.play().catch(() => {});
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function pollSynthesisJob(jobId, options = {}) {
  const autoPlay = options.autoPlay !== false;
  const prefix = options.prefix || "";

  while (true) {
    const { resp, data } = await apiJson(`/api/synthesize_jobs/${jobId}`);
    if (!resp.ok) {
      throw new Error(data.detail || t("msg.queryJobFailed"));
    }

    const percent = Number(data.progress || 0) * 100;
    setProgress(percent);

    if (data.status === "queued") {
      setTtsStatus(t("msg.queueWaitingPrefix", { prefix }));
    } else if (data.status === "running") {
      setTtsStatus(
        t("msg.synthesizingProgressPrefix", {
          prefix,
          done: data.completed_chunks,
          total: data.total_chunks,
        }),
      );
    } else if (data.status === "failed") {
      throw new Error(data.error || t("msg.synthFailed"));
    } else if (data.status === "completed") {
      setProgress(100);
      if (autoPlay) {
        await fetchAndPlayAudio(jobId);
      }
      return data;
    }
    await sleep(1000);
  }
}

async function waitForPlaybackEnd() {
  if (!player.src) return;
  if (player.ended) return;
  await new Promise((resolve) => {
    let done = false;
    const cleanup = () => {
      player.removeEventListener("ended", onDone);
      player.removeEventListener("error", onDone);
      if (resolvePlaybackWait === resolver) {
        resolvePlaybackWait = null;
      }
    };
    const onDone = () => {
      if (done) return;
      done = true;
      cleanup();
      resolve();
    };
    const resolver = () => onDone();
    resolvePlaybackWait = resolver;
    player.addEventListener("ended", onDone, { once: true });
    player.addEventListener("error", onDone, { once: true });
  });
}

async function selectChapterByIndex(index) {
  for (let i = 0; i < chapterSelect.options.length; i += 1) {
    if (Number(chapterSelect.options[i].value) === index) {
      chapterSelect.selectedIndex = i;
      break;
    }
  }
  await loadChapterText(index);
}

function stopAutoChain() {
  if (!chainRunning) return;
  chainStopRequested = true;
  try {
    player.pause();
  } catch (_err) {
  }
  if (resolvePlaybackWait) {
    const fn = resolvePlaybackWait;
    resolvePlaybackWait = null;
    fn();
  }
  setTtsStatus(t("msg.stoppingChain"));
}

async function startAutoChain() {
  if (synthesisInProgress || chainRunning) {
    setTtsStatus(t("msg.taskInProgress"), true);
    return;
  }
  if (!currentDocId) {
    setTtsStatus(t("msg.uploadAndChooseChapter"), true);
    return;
  }
  const startIndex = getSelectedChapterIndex();
  if (startIndex === null) {
    setTtsStatus(t("msg.chooseStartChapter"), true);
    return;
  }

  clearAudio();
  saveConfigToLocalStorage();
  chainRunning = true;
  chainStopRequested = false;
  synthesisInProgress = true;
  updateActionButtons();
  setProgress(0);

  try {
    let currentIndex = startIndex;
    let created = await createSynthesisJob(buildSynthesisPayload(false, currentIndex));
    if (created.alreadyExists && created.message) {
      setTtsStatus(created.message);
    }
    let currentJobId = created.jobId;

    while (!chainStopRequested) {
      await pollSynthesisJob(currentJobId, { autoPlay: false, prefix: formatChapterPrefix(currentIndex) });
      await loadHistoryList();
      if (chainStopRequested) break;

      await selectChapterByIndex(currentIndex);
      await fetchAndPlayAudio(currentJobId);

      const nextIndex = currentIndex + 1;
      let nextJobId = null;
      if (nextIndex < currentChapters.length && prefetchNextToggle.checked) {
        setTtsStatus(t("msg.playingAndPrefetch", { current: currentIndex + 1, next: nextIndex + 1 }));
        const nextCreated = await createSynthesisJob(buildSynthesisPayload(false, nextIndex));
        nextJobId = nextCreated.jobId;
      } else {
        setTtsStatus(t("msg.playingChapter", { index: currentIndex + 1 }));
      }

      await waitForPlaybackEnd();
      if (chainStopRequested) break;

      if (nextIndex >= currentChapters.length) {
        setTtsStatus(t("msg.reachedLastChapter"));
        break;
      }

      currentIndex = nextIndex;
      if (nextJobId) {
        currentJobId = nextJobId;
      } else {
        const nextCreated = await createSynthesisJob(buildSynthesisPayload(false, currentIndex));
        currentJobId = nextCreated.jobId;
      }
    }

    if (chainStopRequested) {
      setTtsStatus(t("msg.chainStopped"));
    }
  } catch (err) {
    setTtsStatus(String(err.message || err), true);
  } finally {
    chainRunning = false;
    chainStopRequested = false;
    synthesisInProgress = false;
    updateActionButtons();
  }
}

async function synthesize(useCustomText) {
  if (synthesisInProgress || chainRunning) {
    setTtsStatus(t("msg.taskInProgress"), true);
    return;
  }
  if (!currentDocId && !chapterText.value.trim()) {
    setTtsStatus(t("msg.uploadOrInputPrompt"), true);
    return;
  }
  clearAudio();
  setProgress(0);
  synthesisInProgress = true;
  updateActionButtons();

  const payload = buildSynthesisPayload(useCustomText);
  setTtsStatus(t("msg.submittingJob"));
  saveConfigToLocalStorage();

  try {
    let created = await createSynthesisJob(payload);
    if (created.alreadyExists && !useCustomText) {
      const tip = created.message || t("msg.duplicateSynthDefault");
      const force = window.confirm(t("msg.duplicateConfirm", { tip }));
      if (force) {
        created = await createSynthesisJob(payload, true);
      } else {
        setTtsStatus(t("msg.replayExisting", { tip }));
      }
    }
    const result = await pollSynthesisJob(created.jobId, { autoPlay: true });
    await loadHistoryList();
    setTtsStatus(t("msg.synthDoneChunks", { chunks: result.total_chunks }));
  } catch (err) {
    setTtsStatus(String(err.message || err), true);
  } finally {
    synthesisInProgress = false;
    updateActionButtons();
  }
}

if (registerBtn) registerBtn.disabled = true;
if (loginBtn) loginBtn.disabled = true;
if (logoutBtn) logoutBtn.disabled = true;

uploadBtn.addEventListener("click", uploadEpub);
bindDocumentsRefreshButton();
chapterSelect.addEventListener("change", async () => {
  const index = getSelectedChapterIndex();
  if (index !== null) await loadChapterText(index);
});

engine.addEventListener("change", async () => {
  if (profileConfigs[engine.value]) {
    applyEngineConfig(profileConfigs[engine.value]);
  }
  applyEngineDefaults();
  await applyVoiceDefaults();
  saveConfigToLocalStorage();
});

[apiKey, endpoint, model, voiceSelect, voiceCustom, speed, outputFormat, instructions, customHeaders, prefetchNextToggle].forEach((el) => {
  el.addEventListener("change", saveConfigToLocalStorage);
});

saveProfileBtn.addEventListener("click", saveProfileConfig);
loadProfileBtn.addEventListener("click", async () => {
  await loadProfileConfig(true);
  setAuthStatus(t("msg.profileLoadedUser", { username: currentUsername }));
});

synthesizeChapterBtn.addEventListener("click", () => synthesize(false));
synthesizeTextBtn.addEventListener("click", () => synthesize(true));
chainStartBtn.addEventListener("click", startAutoChain);
chainStopBtn.addEventListener("click", stopAutoChain);
refreshHistoryBtn.addEventListener("click", loadHistoryList);
if (adminSavePlanBtn) {
  adminSavePlanBtn.addEventListener("click", saveAdminPlan);
}
if (languageSelect) {
  languageSelect.addEventListener("change", () => {
    setLanguage(languageSelect.value);
    if (currentUserIsAdmin) {
      loadAdminConsole().catch(() => {});
    }
  });
}

async function init() {
  ensureDocumentsSection();
  setProgress(0);
  setDownloadDisabled(true);
  renderQuotaStatus(null);
  setAdminPanelVisible(false);
  if (authCard) {
    authCard.hidden = true;
  }
  loadLanguageFromLocalStorage();
  setLanguage(currentLang, false);
  loadConfigFromLocalStorage();
  loadAuthFromLocalStorage();
  applyEngineDefaults();
  setAppEnabled(true);
  setAuthStatus("Local Mode");
  setUploadStatus(t("msg.waitingUpload"));
  setTtsStatus(t("msg.waitingSynthesis"));
  await loadProfileConfig(true);
  await loadQuotaStatus();
  await loadDocumentsList();
  await loadHistoryList();
  updateActionButtons();
}

init();
