import os
import re
from flask import Flask, request, jsonify
from pypdf import PdfReader
import requests

app = Flask(__name__)

# OLLAMAのURL（Docker環境変数から取得）
OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434") + "/api/generate"

# インメモリでドキュメント履歴とコンテキストを保持
uploaded_documents = {}  # { filename: text }

def is_japanese(text):
    if not text:
        return False
    # ひらがな、カタカナ、漢字が含まれているかを判定
    return bool(re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', text))

SYNC_DIR = "/app/data/documents"
os.makedirs(SYNC_DIR, exist_ok=True)

def sync_dir():
    global uploaded_documents
    new_docs = {}
    for filename in os.listdir(SYNC_DIR):
        filepath = os.path.join(SYNC_DIR, filename)
        if not os.path.isfile(filepath):
            continue
            
        try:
            if filename.endswith(".txt"):
                for enc in ["utf-8", "shift_jis", "euc_jp"]:
                    try:
                        with open(filepath, "r", encoding=enc) as f:
                            new_docs[filename] = f.read()
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        new_docs[filename] = f.read()
            elif filename.endswith(".pdf"):
                with open(filepath, "rb") as f:
                    reader = PdfReader(f)
                    text = ""
                    for i, page in enumerate(reader.pages):
                        page_text = page.extract_text()
                        if page_text:
                            text += f"[PDF_PAGE_{i+1}]\n{page_text}\n"
                    new_docs[filename] = text
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            
    uploaded_documents = new_docs
    return list(uploaded_documents.keys())

def get_combined_system_prompt(user_query):
    """資料とユーザーの質問の言語に応じてシステムプロンプトを動的に生成"""
    full_docs_text = "".join(uploaded_documents.values())
    context = ""
    for filename, text in uploaded_documents.items():
        context += f"--- 資料名: {filename} ---\n{text}\n\n"

    # 資料が日本語であり、かつユーザーの入力も日本語である場合は、日本語特化のプロンプトにする
    if is_japanese(user_query) and is_japanese(full_docs_text):
        system_prompt_base = (
            "あなたは誠実で優秀なアシスタントです。"
            "提供された以下の日本語の参考資料の内容に基づいて、ユーザーの質問に日本語で正確に答えてください。\n\n[参考資料]\n"
        )
    else:
        # それ以外の場合は多言語対応のフォールバックプロンプト
        system_prompt_base = (
            "You are a helpful and highly capable assistant. "
            "Based on the provided reference materials, please accurately answer the user's question "
            "in the same language as the question itself.\n\n[Reference Materials]\n"
        )
        
    return system_prompt_base + context

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "ファイルがありません"}), 400
    
    files = request.files.getlist("file")
    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "ファイルが選択されていません"}), 400

    success_files = []
    try:
        for file in files:
            filename = file.filename
            if filename == "":
                continue

            filepath = os.path.join(SYNC_DIR, filename)
            file.save(filepath)
            success_files.append(filename)

        if not success_files:
            return jsonify({"error": "有効なファイルが保存できませんでした"}), 400

        # 保存後、ディレクトリ全体を同期
        history = sync_dir()

        return jsonify({
            "message": f"{len(success_files)}件のファイルを保存し、システムプロンプトを同期しました。",
            "history": history
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/sync", methods=["POST"])
def sync_endpoint():
    try:
        history = sync_dir()
        return jsonify({
            "message": "ディレクトリの同期が完了しました。",
            "history": history
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/delete", methods=["POST"])
def delete_file():
    data = request.json or {}
    filename = data.get("filename")
    if not filename:
        return jsonify({"error": "ファイル名が指定されていません"}), 400
        
    filepath = os.path.join(SYNC_DIR, filename)
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            
        history = sync_dir()
        return jsonify({
            "message": f"{filename} を削除しました。",
            "history": history
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/history", methods=["GET"])
def get_history():
    return jsonify({"history": list(uploaded_documents.keys())})

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json or {}
    user_query = data.get("query", "")
    
    if not user_query:
        return jsonify({"error": "クエリが空です"}), 400

    # 動的に更新されたシステムプロンプトを取得
    full_system_prompt = get_combined_system_prompt(user_query)

    # Ollama (gemma4:12b) へのリクエストパラメータ構築
    # ※Gemmaのプロンプトフォーマットに合わせるため、systemとuserを結合
    prompt = f"<start_of_turn>user\n{full_system_prompt}\n\nユーザーの質問: {user_query}<end_of_turn>\n<start_of_turn>model\n"

    payload = {
        "model": "gemma4:12b",
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response_json = response.json()
        ai_response = response_json.get("response", "")

        # 簡易的な「引用元・ハイライト」のロジック
        # レスポンス内に含まれるキーワードが、どの資料のどの部分（あるいはPDFの何ページ目）にあるかを簡易探索
        source_highlight = "参照資料が見つかりません。全体コンテキストから回答されました。"
        for fname, text in uploaded_documents.items():
            # 回答の断片（例: 最初の20文字など）が資料に含まれるか簡易一致チェック
            # 実用上はキーワードマッチや文脈マッチに拡張可能
            if any(word in text for word in user_query.split() if len(word) > 1):
                source_highlight = f"【引用元資料】: {fname}\n\n{text[:500]}...（以下略）"
                break

        return jsonify({
            "response": ai_response,
            "source": source_highlight
        })

    except Exception as e:
        return jsonify({"error": f"Ollamaとの通信に失敗しました: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)