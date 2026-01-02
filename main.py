import discord
import os
from dotenv import load_dotenv
from janome.tokenizer import Tokenizer
import re
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_server():
    port = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_server)
    t.start()

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# 形態素解析器の初期化
t = Tokenizer()

def count_mora(text):
    """カタカナから音数を数える"""
    parsed = re.sub(r'[ァィゥェォャュョヮ]', '', text)
    return len(parsed)

def check_senryu(text):
    """5-7-5の構造になっているか判定する"""
    # 余計な空白や記号を削除
    text = re.sub(r'[^\w]', '', text)
    
    tokens = list(t.tokenize(text))
    yomis = [token.reading if token.reading != '*' else token.surface for token in tokens]
    
    # 全体の音数を確認
    full_yomi = "".join(yomis)
    if count_mora(full_yomi) < 15: # 短すぎれば無視
        return None

    # 5, 7, 5 の各フェーズをチェック
    counts = [5, 7, 5]
    current_idx = 0
    current_mora = 0
    result_parts = []
    temp_str = ""

    for yomi in yomis:
        current_mora += count_mora(yomi)
        temp_str += yomi
        
        if current_mora == counts[current_idx]:
            result_parts.append(temp_str)
            current_mora = 0
            temp_str = ""
            current_idx += 1
            if current_idx == 3:
                return result_parts
        elif current_mora > counts[current_idx]:
            return None
            
    return None

@client.event
async def on_ready():
    print(f'Logged in as {client.user.name}')

@client.event
async def on_message(message):
    # 自分のメッセージには反応しない
    if message.author == client.user:
        return

    # 川柳かどうか判定
    parts = check_senryu(message.content)
    
    if parts:
        response = (
            f"川柳を検出しました！\n"
            f"「{message.content}」"
        )
        await message.reply(response, mention_author=True)

TOKEN = os.getenv('DISCORD_TOKEN')

if TOKEN is None:
    print("エラー：トークンが読み込めていません。.envファイルを確認してください。")
else:
    print("トークンを読み込みました。ログインを開始します...")

if __name__ == "__main__":
    keep_alive()
    if TOKEN:
        client.run(TOKEN)