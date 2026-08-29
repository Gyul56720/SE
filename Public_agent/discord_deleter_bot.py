import discord
from discord.ext import commands
import os
import asyncio

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=infents if 'infents' in globals() else intents)

TARGET_KEYWORDS = ["김희섭", "삭제"]

@bot.event
async def on_ready():
    print(f"로그인 성공: {bot.user}")
    print("과거 메시지(키워드: 김희섭, 삭제) 삭제를 시작합니다...")
    
    for guild in bot.guilds:
        for channel in guild.text_channels:
            try:
                async for message in channel.history(limit=None):
                    if any(kw in message.content for kw in TARGET_KEYWORDS):
                        await message.delete()
                        print(f"과거 메시지 삭제됨: {message.content}")
                        await asyncio.sleep(1.2)
            except discord.Forbidden:
                print(f"권한 부족: {channel.name}")
            except Exception as e:
                print(f"채널 {channel.name} 삭제 오류: {e}")
    print("정리 완료. 실시간 감시 시작.")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if any(kw in message.content for kw in TARGET_KEYWORDS):
        try:
            await message.delete()
            print(f"실시간 메시지 삭제됨: {message.content}")
        except Exception as e:
            print(f"삭제 오류: {e}")

token = os.getenv("DISCORD_BOT_TOKEN")
if token:
    bot.run(token)
