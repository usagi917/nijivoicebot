import asyncio
import json
import logging
from typing import Dict, List
from urllib.parse import unquote, quote

import aiohttp
from openai import OpenAI, AsyncOpenAI
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from config import (
    OPENAI_API_KEY,
    VOICE_API_TOKEN,
    VOICE_API_BASE_URL,
    DEFAULT_VOICE_ACTOR_ID,
    GPT_MODEL,
    MAX_TOKENS,
    TEMPERATURE,
    VOICE_SPEED,
    VOICE_FORMAT,
    MAX_RETRIES,
    RETRY_DELAY,
)

# ロギングの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# デバッグ用ログを追加
logger.info(f"OPENAI_API_KEY: {OPENAI_API_KEY}")
logger.info(f"VOICE_API_TOKEN: {VOICE_API_TOKEN}")
logger.info(f"VOICE_API_BASE_URL: {VOICE_API_BASE_URL}")

app = FastAPI()

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:5500", "http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI API クライアントの初期化
client = AsyncOpenAI(
    api_key=OPENAI_API_KEY,
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.conversation_history: Dict[str, List[Dict]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.conversation_history[websocket] = []
        logger.info("connection open")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        del self.conversation_history[websocket]
        logger.info("connection closed")

    async def send_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

manager = ConnectionManager()

@app.get("/proxy/audio")
async def proxy_audio(url: str):
    """音声ファイルをプロキシとして中継するエンドポイント"""
    try:
        # URLをデコード
        decoded_url = unquote(url)
        logger.info(f"リクエストされたURL: {decoded_url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(decoded_url) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"音声ファイル取得エラー: ステータス {response.status}, レスポンス: {error_text}")
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"音声ファイルの取得に失敗しました: {error_text}"
                    )
                
                headers = {
                    "Content-Type": "audio/mpeg",
                    "Content-Length": response.headers.get("Content-Length", ""),
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "no-cache"
                }
                
                return StreamingResponse(
                    response.content,
                    headers=headers,
                    media_type="audio/mpeg"
                )
                
    except Exception as e:
        logger.error(f"音声ファイルの取得に失敗: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"音声ファイルの取得中にエラーが発生しました: {str(e)}"
        )

async def generate_voice(text: str, voice_actor_id: str = DEFAULT_VOICE_ACTOR_ID) -> str:
    """音声生成APIを呼び出し、音声URLを取得する"""
    url = f"{VOICE_API_BASE_URL}/voice-actors/{voice_actor_id}/generate-voice"
    headers = {
        "x-api-key": VOICE_API_TOKEN,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    data = {
        "script": text,
        "speed": VOICE_SPEED,
        "format": VOICE_FORMAT
    }

    logger.info(f"Request URL: {url}")
    logger.info(f"Request Headers: {headers}")
    logger.info(f"Request Data: {data}")

    for attempt in range(MAX_RETRIES):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    response_text = await response.text()
                    logger.info(f"音声生成API レスポンス: {response.status} - {response_text}")
                    
                    if response.status == 200:
                        result = await response.json()
                        return result["generatedVoice"]["url"]
                    elif response.status == 401:
                        logger.error("音声生成API認証エラー: APIトークンが無効です")
                        raise Exception("音声生成API認証エラー: APIトークンを確認してください")
                    else:
                        error_msg = f"音声生成API エラー: ステータス {response.status} - {response_text}"
                        logger.error(error_msg)
                        if attempt < MAX_RETRIES - 1:
                            await asyncio.sleep(RETRY_DELAY)
                        else:
                            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"音声生成API エラー: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
                continue
            raise

async def get_gpt_response(messages: List[Dict]) -> str:
    """GPTモデルを使用して応答を生成する"""
    try:
        completion = await client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": "あなたは親切で役立つAIアシスタントです。"},
                *messages
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"GPT API エラー: {str(e)}")
        raise

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            data = json.loads(data)
            
            # 音声データをテキストに変換（この部分は実際のWhisper APIの実装が必要）
            user_message = data["text"]
            
            # 会話履歴の更新
            conversation = manager.conversation_history[websocket]
            conversation.append({"role": "user", "content": user_message})
            
            try:
                # GPT応答の生成
                gpt_response = await get_gpt_response(conversation)
                conversation.append({"role": "assistant", "content": gpt_response})
                
                # 音声の生成
                voice_url = await generate_voice(gpt_response, data.get("voice_actor_id", DEFAULT_VOICE_ACTOR_ID))
                
                # レスポンスの送信
                response = {
                    "text": gpt_response,
                    "voice_url": voice_url
                }
                await manager.send_message(json.dumps(response), websocket)
                
            except Exception as e:
                error_message = {"error": str(e)}
                await manager.send_message(json.dumps(error_message), websocket)
                logger.error(f"Error during processing: {str(e)}")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)