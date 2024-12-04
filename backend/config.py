import os
from dotenv import load_dotenv
import logging

# ロギングの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# .envファイルの読み込み
load_dotenv()

# 環境変数
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
VOICE_API_TOKEN = os.getenv("VOICE_API_TOKEN")

if not VOICE_API_TOKEN:
    logger.error("VOICE_API_TOKEN is missing")
    raise ValueError("VOICE_API_TOKEN environment variable is required")

# APIエンドポイント
VOICE_API_BASE_URL = "https://ai-voice-api-kerb-538219057988.asia-northeast1.run.app/api/platform/v1"
DEFAULT_VOICE_ACTOR_ID = "1"  # 水戸 明日菜のボイスID

# WebSocket設定
WS_HOST = "0.0.0.0"
WS_PORT = 8000

# OpenAI設定
GPT_MODEL = "gpt-4o-mini"
MAX_TOKENS = 150
TEMPERATURE = 0.7

# 音声設定
VOICE_SPEED = "1"  # 推奨スピード値に修正
VOICE_FORMAT = "mp3"

# エラー再試行設定
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

# 環境変数のバリデーション
required_vars = ["OPENAI_API_KEY", "VOICE_API_TOKEN", "VOICE_API_BASE_URL"]
missing_vars = [var for var in required_vars if not globals()[var]]

if missing_vars:
    logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
    raise ValueError(f"Missing environment variables: {', '.join(missing_vars)}")