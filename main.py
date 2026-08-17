import discord
from discord.ext import commands
import os
import wavelink
from dotenv import load_dotenv

load_dotenv()

class MusicBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        # Prefix is statically "-" as requested
        super().__init__(command_prefix="-", intents=intents, help_command=None)

    async def setup_hook(self):
        cogs_dir = os.path.join(os.path.dirname(__file__), 'src', 'cogs')
        os.makedirs(cogs_dir, exist_ok=True)
        
        for filename in os.listdir(cogs_dir):
            if filename.endswith('.py'):
                await self.load_extension(f'src.cogs.{filename[:-3]}')
        
        uri = os.getenv("WAVELINK_URI", "http://127.0.0.1:2333")
        password = os.getenv("WAVELINK_PASSWORD", "youshallnotpass")
        node = wavelink.Node(uri=uri, password=password)
        await wavelink.Pool.connect(nodes=[node], client=self, cache_capacity=100)

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("Connected to Wavelink nodes successfully.")

bot = MusicBot()

if __name__ == "__main__":
    token = os.getenv("BOT_TOKEN")
    if token:
        bot.run(token)
    else:
        print("Please provide a valid BOT_TOKEN.")
