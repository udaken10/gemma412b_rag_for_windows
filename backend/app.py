import os
from flask import Flask, request, jsonify
from pypdf import PdfReader
import requests

app = Flask(__name__)

# OLLAMAのURL（Docker環境変数から取得）
OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434") + "/api/generate"

# インメモリでドキュメント履歴とシステムプロンプト（コンテキスト）を保持
uploaded_documents = {}  # { filename: text }
system_prompt_base = "あなたは誠実で優秀なアシスタントです。提供された以下の参考資料の内容に基づいて、ユーザーの質問に正確に答えてください。\n\n[参考資料]\n"

def get_combined_system_prompt():
    """アップロードされたすべての資料を結合してシステムプロンプトを生成"""
    context = ""
    for filename, text in uploaded_documents.items():
        context += f"--- 資料名: {filename} ---\n{text}\n\n"
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

            # 拡張子に応じてテキスト抽出
            if filename.endswith(".txt"):
                text = file.read().decode("utf-8", errors="ignore")
            elif filename.endswith(".pdf"):
                reader = PdfReader(file)
                text = ""
                for i, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        # ハイライト参照用に、簡易的なページマーカーを埋め込む
                        text += f"[PDF_PAGE_{i+1}]\n{page_text}\n"
            else:
                continue

            # メモリに保存（資料の更新・追記）
            uploaded_documents[filename] = text
            success_files.append(filename)

        if not success_files:
            return jsonify({"error": "有効なファイルが読み込めませんでした"}), 400

        return jsonify({
            "message": f"{len(success_files)}件のファイルを読み込み、システムプロンプトを更新しました。",
            "history": list(uploaded_documents.keys())
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
    full_system_prompt = get_combined_system_prompt()

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