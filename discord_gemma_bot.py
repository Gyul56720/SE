import discord
from discord.ext import commands
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

# [주의] 이 코드는 로컬에 최소 8GB~16GB VRAM을 가진 GPU가 필요합니다.
# 설치: pip install discord.py torch transformers accelerate

TOKEN = 'YOUR_DISCORD_BOT_TOKEN_HERE'

class GemmaBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=discord.Intents.default())
        print("Loading Gemma locally... (This takes memory)")
        self.tokenizer = AutoTokenizer.from_pretrained("google/gemma-2b-it")
        self.model = AutoModelForCausalLM.from_pretrained("google/gemma-2b-it", torch_dtype=torch.float16, device_map="auto")

    async def on_ready(self):
        print(f'Logged in as {self.user}')

    async def on_message(self, message):
        if message.author == self.user:
            return
        
        # 모델 추론
        inputs = self.tokenizer(message.content, return_tensors="pt").to("cuda")
        outputs = self.model.generate(**inputs, max_new_tokens=100)
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        await message.channel.send(response)

# bot = GemmaBot()
# bot.run(TOKEN)
