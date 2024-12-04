# NijiVoice - リアルタイム音声会話システム

WebSocketを利用したリアルタイム音声会話システムです。OpenAI GPTモデルと音声合成APIを使用して、自然な会話を実現します。

## 機能

- リアルタイム音声入力
- GPT-4を使用した自然言語処理
- リアルタイム音声出力
- キャラクター音声の選択機能

## 必要条件

- Python 3.8以上
- Node.js 14以上
- OpenAI API キー
- 音声合成API アクセストークン

## セットアップ

### 環境変数の設定

1. `backend/.env.example`を`backend/.env`にコピーします：
```bash
cd backend
cp .env.example .env
```

2. `.env`ファイルを編集し、必要なAPIキーを設定します：
- `OPENAI_API_KEY`: OpenAIのAPIキー
- `VOICE_API_TOKEN`: 音声合成APIのアクセストークン

### バックエンド

1. Python仮想環境の作成と有効化:
```bash
python -m venv venv
source venv/bin/activate  # Linuxの場合
.\venv\Scripts\activate   # Windowsの場合
```

2. 依存パッケージのインストール:
```bash
cd backend
pip install -r requirements.txt
```

### フロントエンド

1. 依存パッケージのインストール:
```bash
cd frontend
npm install
```

2. 開発サーバーの起動:
```bash
npm run dev
```

## 使用方法

1. バックエンドサーバーの起動:
```bash
cd backend
python app.py
```
2.フロントエンド実行
```
python -m http.server 3000
```
3. ブラウザでアクセス:
```
http://localhost:3000
```

3. マイクボタンをクリックして会話を開始

## 開発者向け情報

### GitHubへのプッシュ

1. 機密情報が含まれる`.env`ファイルは`.gitignore`に設定されており、リポジトリにプッシュされません。
2. 新しい環境変数を追加する場合は、`.env.example`も更新してください。
3. 環境変数の変更をチームメンバーに共有する場合は、`.env.example`を更新してプッシュしてください。

## ライセンス

MIT

## 注意事項

- マイクの使用許可が必要です
- 安定したインターネット接続が必要です
- APIキーは安全に管理してください
  
