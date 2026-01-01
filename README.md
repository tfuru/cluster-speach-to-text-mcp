# cluster-speach-to-text-mcp
Speach-to-Text するための MCP(Model Context Protocol) サーバー

## 概要


## 主な機能 (Tools)

### 音声認識
- `transcribe_audio`: 音声ファイルをテキストに変換します。
- `list_models`: 利用可能なモデル一覧を取得します。

### 録音・デバイス設定
- `list_audio_devices`: 利用可能なマイク（入力デバイス）の一覧を取得します。
- `record_audio`: 指定したデバイスで録音を行います。
  - 保存先パスを省略すると、OSの一時ディレクトリに保存されます。
- `set_default_settings`: デフォルトのモデルや使用するオーディオデバイスを設定・保存します。

## Speech-to-Text サーバー
OpenAI API 互換の whisper サーバーを ローカルで起動して利用します。  
[Speaches](https://speaches.ai/)

## 仮想環境の作成と有効化

```
# 1. 仮想環境を作成（フォルダ名は 'venv' が一般的です）
python3 -m venv venv

# 2. 仮想環境を有効化（アクティベート）
source venv/bin/activate

# (プロンプトの左側に (venv) と表示されれば成功です)
```

## 依存関係のインストール

```
pip install -r requirements.txt
```


## MCPサーバーの設定

設置場所の venv/bin/python のフルパスを指定してください。  
```
{
  "mcpServers": {
    "cluster-speach-to-text-mcp": {
      "command": "[pwd]/server/venv/bin/python",
      "args": [
        "[pwd]/server/main.py"
      ],
      "env": {
        "SPEACHES_API_URL": "http://192.168.10.106:8000/v1",
        "SPEACHES_API_KEY": ""
      },
    }
  }
}
```