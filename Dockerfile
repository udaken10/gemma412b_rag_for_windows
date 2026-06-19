FROM ubuntu:24.04

# 環境変数の設定
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# 必要なパッケージのインストール
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# venvの作成と有効化環境の設定
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 依存ライブラリのコピーとインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションの起動（開発時はCompose側で制御するため、ここではベースのみ）
CMD ["/bin/bash"]