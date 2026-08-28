import discord
import os
import asyncio
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
PUBLIC_CHANNEL_ID = int(os.getenv("DISCORD_PUBLIC_CHANNEL_ID", "1542081072697839618"))

class IDFinderBot(discord.Client):
    async def on_ready(self):
        print(f"[ID Finder] 로그인 성공: {self.user}")
        channel = self.get_channel(PUBLIC_CHANNEL_ID)
        if not channel:
            print(f"[ID Finder] 채널을 찾을 수 없습니다: {PUBLIC_CHANNEL_ID}")
            await self.close()
            return
        
        print(f"[ID Finder] 최근 메시지에서 사용자 ID를 수집합니다...")
        async for message in channel.history(limit=100):
            if not message.author.bot:
                print(f"사용자 이름: {message.author.name}, ID: {message.author.id}, Global Name: {message.author.global_name}")
        
        print("[ID Finder] 수집 완료.")
        await self.close()

intents = discord.Intents.default()
intents.message_content = True
client = IDFinderBot(intents=intents)
client.run(BOT_TOKEN)
