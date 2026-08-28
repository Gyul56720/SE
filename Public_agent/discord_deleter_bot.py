import discord
from discord.ext import commands
import os
import asyncio

# 이 코드는 Discord 봇 실행을 위한 골격입니다.
# 실행을 위해서는 DISCORD_BOT_TOKEN 환경변수가 필요합니다.

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

TARGET_KEYWORD = "김희섭"

@bot.event
async def on_ready():
    print(f"로그인 성공: {bot.user}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if TARGET_KEYWORD in message.content:
        try:
            await message.delete()
            print(f"삭제됨: {message.author}의 메시지 (내용: {message.content})")
        except Exception as e:
            print(f"삭제 오류: {e}")

async def main():
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("에러: DISCORD_BOT_TOKEN 환경변수가 설정되지 않음.")
        return
    await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
