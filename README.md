# Gemma4 RAG System

ローカル環境の Ollama (gemma4:12b) をバックエンドのLLMとして利用し、PDFやTXT形式の資料に基づくRAG（検索拡張生成）チャットを行うためのWebアプリケーションです。
フロントエンドは Gradio、バックエンドは Flask で構築されており、Docker を用いて簡単に環境を構築・起動できます。

## 特徴

- **ローカルLLM活用**: Ollama を介してローカル環境で推論を行うため、データが外部に送信されません。
- **RAG (Retrieval-Augmented Generation) 対応**: PDFファイルやテキストファイルをアップロードし、その内容に基づいてAIが回答を生成します。
- **簡易UI**: Gradio を用いた直感的なモノクロデザインのチャットインターフェース。
- **Docker対応**: バックエンドとフロントエンドを1つのコンテナにまとめ、環境構築を自動化。

## 前提条件

- [Docker](https://www.docker.com/) および [Docker Compose](https://docs.docker.com/compose/)
- [Ollama](https://ollama.ai/) がホストマシン上で起動しており、ポート `11434` でアクセス可能であること
- Ollama 内で `gemma4:12b`（または利用するモデル）が pull されていること
  ```bash
  ollama run gemma4:12b
  ```

## 起動方法

### Windows の場合
リポジトリのルートディレクトリにある `start.bat` をダブルクリックするだけで、自動的にDockerイメージのビルドとコンテナの起動が行われます。

または、コマンドラインから以下のコマンドを実行します：
```bash
docker compose up -d --build
```

### アクセスURL
起動後、ブラウザから以下のURLにアクセスしてください。
- **フロントエンド (Gradio)**: [http://localhost:7860](http://localhost:7860)

## 停止方法

アプリケーションを終了するには、ルートディレクトリにある `stop.bat` をダブルクリックするか、コマンドラインから以下のコマンドを実行します：
```bash
docker compose down
```

## ファイル構成

- `frontend/app.py`: Gradioを用いたUIとユーザー入力処理
- `backend/app.py`: Flaskを用いたファイルのテキスト抽出とOllamaとの連携処理
- `Dockerfile`: アプリケーションの動作環境を構築する設定
- `docker-compose.yml`: ポートマッピングとコンテナ起動設定
- `requirements.txt`: 必要なPythonパッケージ（Flask, Gradio, pypdf, requests 等）
- `start.bat` / `start.sh`: 起動用スクリプト
- `stop.bat`: 停止用スクリプト

## ライセンス
MIT License
