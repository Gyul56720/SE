import discord
import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
PUBLIC_CHANNEL_ID = int(os.getenv("DISCORD_PUBLIC_CHANNEL_ID", "1542081072697839618"))
ADMIN_ID = 732577811172163605

class DeepIDFinderBot(discord.Client):
    async def on_ready(self):
        print(f"[Deep Scan] 채널 탐색 시작...")
        channel = self.get_channel(PUBLIC_CHANNEL_ID)
        if not channel:
            print("[Deep Scan] 채널 접근 실패.")
            await self.close()
            return
            
        unique_guests = set()
        
        # 최근 5000개 메시지까지 탐색
        async for message in channel.history(limit=5000):
            if not message.author.bot and message.author.id != ADMIN_ID:
                if message.author.id not in unique_guests:
                    print(f"발견: {message.author.name} (ID: {message.author.id}, Global: {message.author.global_name})")
                    unique_guests.add(message.author.id)
        
        if not unique_guests:
            print("[Deep Scan] 관리자 외 다른 사용자 기록 없음.")
        await self.close()

intents = discord.Intents.default()
intents.message_content = True
client = DeepIDFinderBot(intents=intents)
client.run(BOT_TOKEN)
