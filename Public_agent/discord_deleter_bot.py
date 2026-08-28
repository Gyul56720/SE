import discord
from discord.ext import commands
import os
import asyncio

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

TARGET_KEYWORD = "김희섭"

@bot.event
async def on_ready():
    print(f"로그인 성공: {bot.user}")
    print("과거 메시지 삭제를 시작합니다...")
    
    for guild in bot.guilds:
        for channel in guild.text_channels:
            try:
                # 과거 메시지 순회 및 삭제
                async for message in channel.history(limit=None): # limit=None은 제한 없이 모두 스캔
                    if TARGET_KEYWORD in message.content:
                        await message.delete()
                        print(f"과거 메시지 삭제됨: {message.content}")
                        await asyncio.sleep(1.2) # API 레이트 리미트 방지
            except discord.Forbidden:
                print(f"권한 부족: {channel.name}")
            except Exception as e:
                print(f"채널 {channel.name} 삭제 오류: {e}")
    print("과거 메시지 정리 완료. 실시간 감시 시작.")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if TARGET_KEYWORD in message.content:
        try:
            await message.delete()
            print(f"실시간 메시지 삭제됨: {message.content}")
        except Exception as e:
            print(f"삭제 오류: {e}")

token = os.getenv("DISCORD_BOT_TOKEN")
if token:
    bot.run(token)
