cat << 'EOF' > main.py
import discord
import os
from janome.tokenizer import Tokenizer
from dotenv import load_dotenv
import re
from collections import deque
import asyncio

# 環境変数を読み込み
load_dotenv()
t = Tokenizer()

LOG_GUILD_ID = 1457218647096426601    
LOG_CHANNEL_ID = 1457218647914188873  

message_cache = {}

FIX_READING = {
    "次": "ツギ", "安心": "アンシン", "設定": "セッテイ", 
    "見覚え": "ミオボエ", "振り返っ": "フリカエッ", "全体": "ゼンタイ"
}

def count_mora(text):
    parsed = re.sub(r'[ャュョァィゥェォヮ]', '', text)
    return len(parsed)

def is_valid_start(token):
    pos = token.part_of_speech.split(',')[0]
    pos_detail = token.part_of_speech.split(',')[1]
    if pos in ['助詞', '助動詞', '記号', '接尾辞', '非自立'] or pos_detail == '数':
        return False
    return True

class MyClient(discord.Client):
    async def update_status(self):
        guild_count = len(self.guilds)
        game = discord.Game(f"{guild_count}サーバーで稼働中")
        await self.change_presence(status=discord.Status.online, activity=game)
        print(f'ステータス更新: {guild_count}サーバー')

    async def on_ready(self):
        print(f'--------------------------------------')
        print(f'川柳Bot起動')
        print(f'--------------------------------------')
        await self.update_status()

    async def on_guild_join(self, guild):
        await self.update_status()

    async def on_guild_remove(self, guild):
        await self.update_status()

    async def on_message(self, message):
        if message.author.bot: return
        ch_id = message.channel.id
        if ch_id not in message_cache:
            message_cache[ch_id] = deque(maxlen=11)
        
        message_cache[ch_id].append(f"{message.author.display_name}({message.author.id}): {message.content}")
        
        clean_text = re.sub(r'[0-9０-９一二三四五六七八九十]', '', message.content)
        clean_text = re.sub(r'[^\wー]', '', clean_text)
        if not clean_text: return
        tokens = list(t.tokenize(clean_text))
        for i in range(len(tokens)):
            if not is_valid_start(tokens[i]): continue
            s1, c1 = "", 0
            for j in range(i, len(tokens)):
                y1 = FIX_READING.get(tokens[j].surface) or (tokens[j].reading if tokens[j].reading != '*' else tokens[j].surface)
                s1 += tokens[j].surface; c1 += count_mora(y1)
                if c1 == 5:
                    if (j + 1) >= len(tokens) or not is_valid_start(tokens[j+1]): continue
                    s2, c2 = "", 0
                    for k in range(j + 1, len(tokens)):
                        y2 = FIX_READING.get(tokens[k].surface) or (tokens[k].reading if tokens[k].reading != '*' else tokens[k].surface)
                        s2 += tokens[k].surface; c2 += count_mora(y2)
                        if c2 == 7:
                            if (k + 1) >= len(tokens) or not is_valid_start(tokens[k+1]): continue
                            s3, c3 = "", 0
                            for l in range(k + 1, len(tokens)):
                                y3 = FIX_READING.get(tokens[l].surface) or (tokens[l].reading if tokens[l].reading != '*' else tokens[l].surface)
                                s3 += tokens[l].surface; c3 += count_mora(y3)
                                if c3 == 5:
                                    is_end = False
                                    if (l + 1) == len(tokens): is_end = True
                                    else:
                                        next_t = tokens[l+1]
                                        if next_t.part_of_speech.split(',')[0] == '記号' or next_t.surface in ['で', 'が', 'し', 'も', 'と', 'ね', 'よ']:
                                            is_end = True
                                    if not is_end: continue
                                    await message.reply(f"川柳を検出しました！\n『 {s1} {s2} {s3} 』")
                                    asyncio.create_task(self.wait_and_log(message, s1, s2, s3))
                                    return
                        elif c2 > 7: break
                elif c1 > 5: break

    async def wait_and_log(self, message, s1, s2, s3):
        await asyncio.sleep(120) 
        log_guild = self.get_guild(LOG_GUILD_ID)
        log_channel = log_guild.get_channel(LOG_CHANNEL_ID) if log_guild else None
        if not log_channel: return
        thread_name = f"{message.guild.name} - #{message.channel.name}"
        thread = discord.utils.get(log_channel.threads, name=thread_name)
        if thread is None:
            thread = await log_channel.create_thread(name=thread_name, type=discord.ChannelType.public_thread, auto_archive_duration=10080)
        elif thread.archived: await thread.edit(archived=False)
        context = "\n".join(list(message_cache.get(message.channel.id, [])))
        
        log_text = (
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"**📺 チャンネル: #{message.channel.name}**\n"
            f"--- 前後の文脈 (最大11件) ---\n"
            f"```\n{context}\n```\n"
            f"✨ **詠まれた句: 『 {s1} / {s2} / {s3} 』**\n"
            f"👤 詠み手: {message.author.mention} ({message.author.id}) | [ジャンプ]({message.jump_url})"
        )
        await thread.send(log_text)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
client = MyClient(intents=intents)
client.run(os.getenv('DISCORD_TOKEN'))
EOF
