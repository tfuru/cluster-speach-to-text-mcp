import os
from mcp.server.fastmcp import FastMCP
from openai import AsyncOpenAI
import httpx
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import asyncio
import tempfile
import time

# サーバーのインスタンスを作成
mcp = FastMCP("ClusterSpeachToTextMcp")

# OpenAIクライアントの初期化は不要になったため削除
# デフォルトはローカルのSpeachesサーバー
SPEACHES_API_URL = os.getenv("SPEACHES_API_URL", "http://localhost:8000/v1")
SPEACHES_API_KEY = os.getenv("SPEACHES_API_KEY", "cant-be-empty")

import json

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_config(config: dict):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)

@mcp.tool()
async def set_default_settings(model: str = None, audio_device: int = None) -> str:
    """
    デフォルトの設定を保存します。
    
    Args:
        model: デフォルトで使用するモデルID (オプション)
        audio_device: デフォルトで使用するオーディオ入力デバイスID (オプション)
    """
    config = load_config()
    messages = []
    
    if model is not None:
        config["default_model"] = model
        messages.append(f"Default model set to: {model}")
        
    if audio_device is not None:
        config["default_audio_device"] = audio_device
        messages.append(f"Default audio device set to: {audio_device}")
    
    if not messages:
        return "No settings provided to update."

    try:
        save_config(config)
        return "\n".join(messages)
    except Exception as e:
        return f"Error saving settings: {str(e)}"

@mcp.tool()
async def transcribe_audio(audio_path: str, model: str = None) -> str:
    """
    録音された音声ファイルをテキストに変換します。
    
    Args:
        audio_path: 音性ファイルの絶対パス (例: /path/to/audio.wav)
        model: 使用するモデルのID (指定しない場合はデフォルト設定を使用)
    """
    if not os.path.exists(audio_path):
        return f"Error: File not found at {audio_path}"

    target_model = model
    if target_model is None:
        config = load_config()
        target_model = config.get("default_model", "whisper-1")

    try:
        # Speaches docs: POST /v1/audio/transcriptions
        # curl -F "file=@audio.wav" -F "model=..."
        url = f"{SPEACHES_API_URL.rstrip('/')}/audio/transcriptions"
        
        # open file in rb mode
        files = {'file': open(audio_path, 'rb')}
        data = {'model': target_model}
        headers = {}
        if SPEACHES_API_KEY:
            headers["Authorization"] = f"Bearer {SPEACHES_API_KEY}"

        async with httpx.AsyncClient() as client:
            # First request might take time to load model, so increasing timeout
            response = await client.post(url, files=files, data=data, headers=headers, timeout=300.0)
            
            if response.status_code != 200:
                return f"Error: {response.status_code} - {response.text}"
                
            return response.json().get("text", "")

    except Exception as e:
        return f"Error during transcription: {str(e)}"

@mcp.tool()
async def list_models() -> str:
    """
    利用可能なモデルの一覧を取得します。
    """
    try:
        # Speaches uses /v1/registry for model listings which isn't standard OpenAI
        # So we use httpx directly
        registry_url = f"{SPEACHES_API_URL.rstrip('/')}/registry"
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(registry_url)
            response.raise_for_status()
            data = response.json()
            
        models = data.get("data", [])
        return "\n".join([model["id"] for model in models])
    except Exception as e:
        return f"Error listing models: {str(e)}"

@mcp.tool()
async def list_audio_devices() -> str:
    """
    利用可能なオーディオ入力デバイスの一覧を返します。
    """
    try:
        devices = sd.query_devices()
        input_devices = []
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                input_devices.append(f"{i}: {device['name']}")
        
        if not input_devices:
            return "No input devices found."
            
        return "\n".join(input_devices)
    except Exception as e:
        return f"Error listing devices: {str(e)}"

@mcp.tool()
async def record_audio(duration: float, output_path: str = None, device: int = None) -> str:
    """
    指定されたデバイスで音声を録音し、WAVファイルとして保存します。
    
    Args:
        duration: 録音時間（秒）
        output_path: 保存先の絶対パス (例: /path/to/recording.wav)。省略時は一時ファイルを作成します。
        device: デバイスID (list_audio_devicesで確認可能。指定しない場合はデフォルト)
    """
    try:
        # 保存先の決定
        target_path = output_path
        if target_path is None:
            filename = f"recording_{int(time.time())}.wav"
            target_path = os.path.join(tempfile.gettempdir(), filename)

        # サンプリングレート
        fs = 44100
        
        # デバイスが指定されていない場合、設定からデフォルトを取得試行
        target_device = device
        if target_device is None:
            config = load_config()
            target_device = config.get("default_audio_device")
        
        def _record():
            # 録音開始
            recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, device=target_device, dtype='float32')
            sd.wait()  # 録音完了待ち
            return recording

        # 非同期で録音を実行（メインスレッドをブロックしないため）
        # print(f"Starting recording for {duration} seconds...")
        recording = await asyncio.to_thread(_record)
        
        # 保存
        write(target_path, fs, recording)
        
        return f"Recording saved to {target_path}"
    except Exception as e:
        return f"Error recording audio: {str(e)}"

# MCPサーバーを起動
if __name__ == "__main__":
    mcp.run()