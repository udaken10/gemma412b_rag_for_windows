import gradio as gr
import requests
import os

BACKEND_URL = "http://localhost:5000"

# シンプルな白黒デザインのテーマ定義
monochrome_theme = gr.themes.Base(
    primary_hue="slate",
    secondary_hue="slate",
    neutral_hue="slate",
).set(
    body_background_fill="*neutral_50",
    block_background_fill="*white",
    block_border_width="1px",
    block_border_color="*neutral_200",
    button_primary_background_fill="*neutral_900",
    button_primary_text_color="*white",
    button_secondary_background_fill="*white",
    button_secondary_text_color="*neutral_900",
    button_secondary_border_color="*neutral_300"
)

def upload_file_fn(file):
    if file is None:
        return "ファイルが選択されていません。", gr.update()
    
    filename = os.path.basename(file.name)
    with open(file.name, "rb") as f:
        files = {"file": (filename, f)}
        try:
            res = requests.post(f"{BACKEND_URL}/upload", files=files)
            res_data = res.json()
            if res.status_code == 200:
                history_list = res_data.get("history", [])
                history_md = "\n".join([f"- {item}" for item in history_list])
                return f"成功: {res_data['message']}", history_md
            else:
                return f"エラー: {res_data.get('error')}", gr.update()
        except Exception as e:
            return f"バックエンドに接続できません: {str(e)}", gr.update()

def refresh_history():
    try:
        res = requests.get(f"{BACKEND_URL}/history")
        if res.status_code == 200:
            history_list = res.json().get("history", [])
            return "\n".join([f"- {item}" for item in history_list])
    except:
        pass
    return "履歴を取得できませんでした。"

def chat_fn(query):
    if not query:
        return "質問を入力してください。", "", ""
    try:
        res = requests.post(f"{BACKEND_URL}/chat", json={"query": query})
        res_data = res.json()
        if res.status_code == 200:
            return res_data.get("response"), res_data.get("source"), "処理完了"
        else:
            return f"エラー: {res_data.get('error')}", "", "エラー発生"
    except Exception as e:
        return f"バックencodedに接続失敗: {str(e)}", "", "通信エラー"

# Gradio インターフェースの構築
with gr.Blocks(theme=monochrome_theme, title="Gemma4 RAG System") as demo:
    gr.Markdown("# Gemma4:12b RAG System")
    
    with gr.Row():
        # 左カラム: 資料管理・表示系
        with gr.Column(scale=1):
            gr.Markdown("### 📄 資料アップロード & 履歴")
            file_input = gr.File(label="PDFまたはTXTファイルを選択", file_types=[".pdf", ".txt"])
            upload_btn = gr.Button("資料をシステムプロンプトに同期", variant="secondary")
            upload_status = gr.Textbox(label="アップロードステータス", interactive=False)
            
            gr.Markdown("### 🗂️ アップロード済み資料履歴")
            history_display = gr.Markdown("*履歴はまだありません*")
            reload_btn = gr.Button("履歴の再読み込み・更新", variant="secondary")
            
            gr.Markdown("### 🔍 引用元1次資料 / 参照場所ハイライト")
            source_display = gr.Textbox(label="マッチしたソーステキスト（上位コンテキスト）", lines=10, interactive=False)

        # 右カラム: チャット・メイン表示系
        with gr.Column(scale=2):
            gr.Markdown("### 💬 対話ウィンドウ")
            chat_input = gr.Textbox(label="質問を入力してください", placeholder="例: アップロードした資料について教えてください...", lines=3)
            submit_btn = gr.Button("送信", variant="primary")
            
            chat_output = gr.Textbox(label="Gemma4 レスポンス表示", lines=12, interactive=False)
            system_status = gr.Label(label="ステータス")

    # イベントハンドラーの定義
    upload_btn.click(
        fn=upload_file_fn,
        inputs=[file_input],
        outputs=[upload_status, history_display]
    )
    
    reload_btn.click(
        fn=refresh_history,
        inputs=[],
        outputs=[history_display]
    )

    submit_btn.click(
        fn=chat_fn,
        inputs=[chat_input],
        outputs=[chat_output, source_display, system_status]
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)