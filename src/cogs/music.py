import discord
from discord.ext import commands
import wavelink
from src.checks import check_chat
from typing import cast
import random

class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_player(self, ctx: commands.Context) -> wavelink.Player:
        player: wavelink.Player = cast(wavelink.Player, ctx.guild.voice_client)
        
        if not ctx.author.voice:
            await ctx.send("❌ يجب أن تكون في غرفة البوت الصوتية لاستخدام الأوامر.", delete_after=10)
            return None
            
        strict_channel_id = getattr(self.bot, 'channel_id', None)
        if strict_channel_id and ctx.author.voice.channel.id != int(strict_channel_id):
            await ctx.send(f"❌ عذراً، هذا البوت مخصص فقط في هذه الغرفة: <#{strict_channel_id}>", delete_after=10)
            return None

        if player:
            if ctx.author.voice.channel.id != player.channel.id:
                await ctx.send("❌ أنت لست في نفس الغرفة الصوتية الخاصة بالبوت.", delete_after=10)
                return None
            return player
        else:
            try:
                player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
                return player
            except Exception as e:
                await ctx.send(f"❌ خطأ بالاتصال: `{e}`")
                return None

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.id != self.bot.user.id:
            return
            
        strict_channel_id = getattr(self.bot, 'channel_id', None)
        if not strict_channel_id:
            return
            
        home_channel_id = int(strict_channel_id)
        if after.channel is None or after.channel.id != home_channel_id:
            guild = member.guild
            home_channel = guild.get_channel(home_channel_id)
            if home_channel:
                try:
                    if guild.voice_client:
                        await guild.voice_client.disconnect(force=True)
                    await home_channel.connect(cls=wavelink.Player)
                except Exception:
                    pass

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        pass # In case we want to announce globally

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        play_letter = getattr(self.bot, 'play_letter', None)
        if not play_letter:
            return

        content = message.content.strip()
        prefix = f"{play_letter.lower()} "
        
        if content.lower().startswith(prefix):
            query = content[len(prefix):].strip()
            if not query:
                return
            
            ctx = await self.bot.get_context(message)
            play_cmd = self.bot.get_command("play")
            if play_cmd:
                try:
                    if await play_cmd.can_run(ctx):
                        await self.play(ctx, query=query)
                except commands.CommandError:
                    pass

    @commands.command(name="play", aliases=["p"])
    @commands.check(check_chat)
    async def play(self, ctx: commands.Context, *, query: str):
        player = await self.get_player(ctx)
        if not player: return

        if not hasattr(player, "autoplay") or player.autoplay != wavelink.AutoPlayMode.enabled:
            player.autoplay = wavelink.AutoPlayMode.partial

        try:
            tracks: wavelink.Search = await wavelink.Playable.search(query, source=wavelink.TrackSource.YouTube)
        except wavelink.LavalinkLoadException:
            try:
                tracks: wavelink.Search = await wavelink.Playable.search(query, source=wavelink.TrackSource.SoundCloud)
            except Exception as e:
                return await ctx.send(f"❌ لم أتمكن من تشغيل المقطع أو أن المنصة محظورة.")
            
        if not tracks:
            return await ctx.send("❌ لم أتمكن من إيجاد المقطع.", delete_after=10)

        if isinstance(tracks, wavelink.Playlist):
            added: int = await player.queue.put_wait(tracks)
            await ctx.send(f"✅ تمت إضافة القائمة: **{tracks.name}** ({added} مقاطع)")
        else:
            track: wavelink.Playable = tracks[0]
            await player.queue.put_wait(track)
            await ctx.send(f"✅ تمت الإضافة للقائمة: **{track.title}**")

        if not player.playing:
            await player.play(player.queue.get())

    @commands.command(name="stop", aliases=["leave_music"])
    @commands.check(check_chat)
    async def stop(self, ctx: commands.Context):
        player = cast(wavelink.Player, ctx.guild.voice_client)
        if player:
            player.queue.clear()
            await ctx.send("✅ تم إيقاف التشغيل وحذف القائمة.")

    @commands.command(name="skip", aliases=["s","سكب"])
    @commands.check(check_chat)
    async def skip(self, ctx: commands.Context):
        player = cast(wavelink.Player, ctx.guild.voice_client)
        if not player or not player.playing:
            return await ctx.send("❌ لا يوجد مقطع يتم تشغيله.")
        
        await player.skip(force=True)
        await ctx.send("⏩ تم التخطي بنجاح.")

    @commands.command(name="volume", aliases=["vol","صوت"])
    @commands.check(check_chat)
    async def volume(self, ctx: commands.Context, vol: int):
        player = cast(wavelink.Player, ctx.guild.voice_client)
        if not player:
            return await ctx.send("❌ لا يوجد مشغل حالياً.")
        if vol < 0 or vol > 1000:
            return await ctx.send("❌ يرجى وضع رقم بين 0 و 1000")
        
        await player.set_volume(vol)
        await ctx.send(f"🔊 تم تغيير مستوى الصوت إلى: `{vol}%`")

    @commands.command(name="nowplaying", aliases=["np","الان"])
    @commands.check(check_chat)
    async def nowplaying(self, ctx: commands.Context):
        player = cast(wavelink.Player, ctx.guild.voice_client)
        if not player or not player.playing:
            return await ctx.send("❌ لا يوجد مقطع يتم تشغيله.")
        
        track = player.current
        embed = discord.Embed(title="🎶 المقطع الحالي", description=f"**[{track.title}]({track.uri})**", color=discord.Color.purple())
        embed.add_field(name="المدة", value=f"`{track.length // 60000}:{(track.length // 1000) % 60:02d}`")
        if track.artwork:
            embed.set_thumbnail(url=track.artwork)
        await ctx.send(embed=embed)

    @commands.command(name="queue", aliases=["q","قائمة"])
    @commands.check(check_chat)
    async def queue(self, ctx: commands.Context):
        player = cast(wavelink.Player, ctx.guild.voice_client)
        if not player or player.queue.is_empty:
            return await ctx.send("❌ القائمة فارغة حالياً.")
        
        q_list = list(player.queue)
        desc = ""
        for i, track in enumerate(q_list[:10], 1):
            desc += f"**{i}.** {track.title}\n"
        
        if len(q_list) > 10:
            desc += f"\n*... وهناك {len(q_list) - 10} مقاطع أخرى*"
            
        embed = discord.Embed(title="القائمة الحالية", description=desc, color=discord.Color.blue())
        await ctx.send(embed=embed)

    @commands.command(name="clear", aliases=["حذف"])
    @commands.check(check_chat)
    async def clear_queue(self, ctx: commands.Context):
        player = cast(wavelink.Player, ctx.guild.voice_client)
        if not player:
            return await ctx.send("❌ لا يوجد مشغل حالياً.")
        
        player.queue.clear()
        await ctx.send("✅ تم حذف جميع المقاطع من القائمة.")

    @commands.command(name="pause", aliases=["وقف"])
    @commands.check(check_chat)
    async def pause(self, ctx: commands.Context):
        player = cast(wavelink.Player, ctx.guild.voice_client)
        if player and player.playing and not player.paused:
            await player.pause(True)
            await ctx.send("⏸️ تم الإيقاف المؤقت.")

    @commands.command(name="resume", aliases=["استئناف"])
    @commands.check(check_chat)
    async def resume(self, ctx: commands.Context):
        player = cast(wavelink.Player, ctx.guild.voice_client)
        if player and player.paused:
            await player.pause(False)
            await ctx.send("▶️ تم استكمال التشغيل.")

    @commands.command(name="autoplay", aliases=["ap", "تشغيل تلقائي"])
    @commands.check(check_chat)
    async def autoplay(self, ctx: commands.Context):
        player = cast(wavelink.Player, ctx.guild.voice_client)
        if not player:
            return await ctx.send("❌ البوت لا يعمل حالياً.")
        
        if player.autoplay == wavelink.AutoPlayMode.enabled:
            player.autoplay = wavelink.AutoPlayMode.partial
            await ctx.send("🔄 تم إيقاف التشغيل التلقائي.")
        else:
            player.autoplay = wavelink.AutoPlayMode.enabled
            await ctx.send("✅ تم تفعيل التشغيل التلقائي للاستمرار بتشغيل مقاطع مشابهة.")

    @commands.command(name="loop", aliases=["تكرار"])
    @commands.check(check_chat)
    async def loop(self, ctx: commands.Context):
        player = cast(wavelink.Player, ctx.guild.voice_client)
        if not player: return
        
        if player.queue.mode == wavelink.QueueMode.loop:
            player.queue.mode = wavelink.QueueMode.normal
            await ctx.send("🔃 تم إيقاف التكرار.")
        else:
            player.queue.mode = wavelink.QueueMode.loop
            await ctx.send("🔂 تم تفعيل تكرار المقطع الحالي.")

    @commands.command(name="seek")
    @commands.check(check_chat)
    async def seek(self, ctx: commands.Context, seconds: int):
        player = cast(wavelink.Player, ctx.guild.voice_client)
        if not player or not player.playing:
            return await ctx.send("❌ لا يوجد مقطع للتقديم.")
        
        await player.seek(seconds * 1000)
        await ctx.send(f"⏩ تم التقديم إلى {seconds} ثانية.")

    @commands.command(name="filters", aliases=["فلاتر"])
    @commands.check(check_chat)
    async def filters(self, ctx: commands.Context, filter_name: str = "none"):
        player = cast(wavelink.Player, ctx.guild.voice_client)
        if not player: return

        if filter_name.lower() == "none":
            filters: wavelink.Filters = player.filters
            filters.reset()
            await player.set_filters(filters)
            return await ctx.send("✅ تم إزالة الفلاتر.")

        filters = player.filters
        if filter_name.lower() == "bass":
            filters.equalizer.set(bands=[(0, 0.25), (1, 0.25), (2, 0.20)])
        elif filter_name.lower() == "nightcore":
            filters.timescale.set(pitch=1.2, speed=1.1, rate=1)
        else:
            return await ctx.send("❌ الفلاتر المتاحة: `bass, nightcore, none`")
            
        await player.set_filters(filters)
        await ctx.send(f"✅ تم تفعيل فلتر: `{filter_name}`")

    @commands.command(name="search", aliases=["بحث"])
    @commands.check(check_chat)
    async def search(self, ctx: commands.Context, *, query: str):
        try:
            tracks: wavelink.Search = await wavelink.Playable.search(query, source=wavelink.TrackSource.YouTube)
        except wavelink.LavalinkLoadException:
            try:
                tracks: wavelink.Search = await wavelink.Playable.search(query, source=wavelink.TrackSource.SoundCloud)
            except Exception as e:
                return await ctx.send(f"❌ خطأ من السيرفر، ربما المنصة محظورة.")
                
        if not tracks:
            return await ctx.send("❌ لم أتمكن من إيجاد نتائج.")
        
        desc = ""
        for i, track in enumerate(tracks[:5], 1):
            desc += f"**{i}.** {track.title}\n"
            
        embed = discord.Embed(title="🔍 نتائج البحث (اختر 1-5)", description=desc, color=discord.Color.green())
        msg = await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
            
        try:
            resp = await self.bot.wait_for("message", check=check, timeout=30.0)
            choice = int(resp.content) - 1
            if 0 <= choice < min(5, len(tracks)):
                player = await self.get_player(ctx)
                if not player: return
                track = tracks[choice]
                await player.queue.put_wait(track)
                await ctx.send(f"✅ تمت إضافة: **{track.title}**")
                if not player.playing:
                    await player.play(player.queue.get())
            else:
                await ctx.send("❌ اختيار خاطئ.")
        except TimeoutError:
            await ctx.send("⏳ انتهى وقت الاختيار.", delete_after=5)

    @commands.command(name="shuffle", aliases=["خلط"])
    @commands.check(check_chat)
    async def shuffle(self, ctx: commands.Context):
        player = cast(wavelink.Player, ctx.guild.voice_client)
        if not player or player.queue.is_empty:
            return await ctx.send("❌ القائمة فارغة حالياً.")
            
        player.queue.shuffle()
        await ctx.send("🔀 تم خلط القائمة بنجاح.")

    @commands.command(name="help", aliases=["مساعدة", "اوامر", "أوامر"])
    @commands.check(check_chat)
    async def help_cmd(self, ctx: commands.Context):
        embed = discord.Embed(
            title="📜 قائمة الأوامر", 
            description="إليك قائمة بجميع أوامر البوت المتاحة:", 
            color=discord.Color.blue()
        )
        
        prefix = ctx.prefix
        play_letter = getattr(self.bot, 'play_letter', None)
        play_hint = f"أو ببساطة `{play_letter} ` قبل اسم المقطع" if play_letter else ""
        
        commands_list = [
            ("🎵 تشغيل مقطع", f"`{prefix}play` أو `{prefix}p` {play_hint}"),
            ("⏩ تخطي المقطع", f"`{prefix}skip` أو `{prefix}s` أو `{prefix}سكب`"),
            ("⏹️ إيقاف وحذف القائمة", f"`{prefix}stop`"),
            ("⏸️ إيقاف مؤقت", f"`{prefix}pause` أو `{prefix}وقف`"),
            ("▶️ استئناف", f"`{prefix}resume` أو `{prefix}استئناف`"),
            ("📜 عرض القائمة", f"`{prefix}queue` أو `{prefix}q` أو `{prefix}قائمة`"),
            ("🗑️ مسح القائمة", f"`{prefix}clear` أو `{prefix}حذف`"),
            ("ℹ️ المقطع الحالي", f"`{prefix}nowplaying` أو `{prefix}np` أو `{prefix}الان`"),
            ("🔊 مستوى الصوت", f"`{prefix}volume` أو `{prefix}vol` أو `{prefix}صوت`"),
            ("🔄 تشغيل تلقائي", f"`{prefix}autoplay` أو `{prefix}ap` أو `{prefix}تشغيل تلقائي`"),
            ("🔂 تكرار المقطع", f"`{prefix}loop` أو `{prefix}تكرار`"),
            ("🔀 خلط القائمة", f"`{prefix}shuffle` أو `{prefix}خلط`"),
            ("⏩ تقديم المقطع", f"`{prefix}seek`"),
            ("🔍 بحث", f"`{prefix}search` أو `{prefix}بحث`"),
            ("🎛️ فلاتر الصوت", f"`{prefix}filters` أو `{prefix}فلاتر` (bass, nightcore, none)"),
        ]
        
        for name, value in commands_list:
            embed.add_field(name=name, value=value, inline=False)
            
        embed.set_footer(text="شكراً لاستخدامك البوت 🎵")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(MusicCog(bot))
