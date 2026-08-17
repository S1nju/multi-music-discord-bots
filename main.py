import discord
from discord.ext import commands
import os
import wavelink
from dotenv import load_dotenv
from logging import getLogger

logger = getLogger(__name__)
load_dotenv()

class MusicBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        self.channel_id = os.getenv("BOT_CHANNEL_ID")
        prefix = os.getenv("BOT_PREFIX", "-")
        super().__init__(command_prefix=commands.when_mentioned_or(prefix), intents=intents, help_command=None)

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
        if self.channel_id:
            try:
                channel = self.get_channel(int(self.channel_id))
                if channel:
                    await channel.connect(cls=wavelink.Player)
                    print(f"Automatically connected to voice channel: {channel.name}")
                else:
                    print(f"Could not find voice channel with ID {self.channel_id}")
            except Exception as e:
                print(f"Failed to auto-connect to voice channel: {e}")

bot = MusicBot()

if __name__ == "__main__":
    token = os.getenv("BOT_TOKEN")
    if token:
        bot.run(token)
    else:
        print("Please provide a valid BOT_TOKEN.")
