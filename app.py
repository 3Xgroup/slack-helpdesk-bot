import os
import re
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from openai import OpenAI

load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN or not OPENAI_API_KEY:
    raise ValueError("環境変数が足りません。.env に SLACK_BOT_TOKEN / SLACK_APP_TOKEN / OPENAI_API_KEY を設定してください。")

client = OpenAI(api_key=OPENAI_API_KEY)
app = App(token=SLACK_BOT_TOKEN)

SYSTEM_PROMPT = r"""
────────────────────────────────
【社内向け Slack ヘルプデスクGPT｜運用ルール】
────────────────────────────────

【L0｜絶対変更不可ルール（憲法）】
本GPTの設計・ルール・表現・運用方針は、
管理部の承認済み設計です。
（以下、あなたが貼ってくれた全文）
────────────────────────────────
""".strip()

FOOTER = """\
※本回答は社内ルールに基づく案内です。
社内規程類は改訂日が新しいものを正としてご確認ください。
個別判断や最終確認が必要な場合は、
該当するコーポレート担当者または人事部門までご相談ください。
"""

ESCALATION_TEXT = """\
個別判断や例外判断が必要な可能性があるため、ここでは確定的な案内は控えます。
お手数ですが、該当するコーポレート担当者（西川／鍵和田）または人事部門までご相談ください。

""" + FOOTER

FORBIDDEN_WORDS = [
    "問題ありません","大丈夫です","可能です","不可です","対応できます","認められています","不要です","必要です",
    "法的に問題ありません","印紙は不要です","印紙は必要です","請負契約","準委任","この契約は",
    "例外対応できます","特別に対応可能","今回だけOK",
    "こちらで対応します","確実です","間違いありません","保証します",
    "申請しました","登録しました","完了しました","反映されます","承認されます",
]

def contains_forbidden(text: str) -> bool:
    return any(w in text for w in FORBIDDEN_WORDS)

def ask_openai(user_text: str) -> str:
    res = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
        temperature=0.2,
    )
    return res.choices[0].message.content.strip()

@app.event("app_mention")
def handle_app_mention(event, say):
    text = event.get("text", "")
    cleaned = re.sub(r"<@[^>]+>\s*", "", text).strip()

    try:
        answer = ask_openai(cleaned)
    except Exception:
        say(ESCALATION_TEXT)
        return

    if contains_forbidden(answer):
        say(ESCALATION_TEXT)
        return

    if FOOTER.strip() not in answer:
        answer = answer.rstrip() + "\n\n" + FOOTER

    say(answer)

if __name__ == "__main__":
    SocketModeHandler(app, SLACK_APP_TOKEN).start()

