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
        if not player:
            try:
                if ctx.author.voice:
                    player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
                else:
                    await ctx.send("❌ يجب أن تكون في غرفة صوتية.")
                    return None
            except Exception as e:
                await ctx.send(f"❌ خطأ بالاتصال: `{e}`")
                return None
        return player

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        pass # In case we want to announce globally

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

    @commands.command(name="skip", aliases=["s"])
    @commands.check(check_chat)
    async def skip(self, ctx: commands.Context):
        player = cast(wavelink.Player, ctx.guild.voice_client)
        if not player or not player.playing:
            return await ctx.send("❌ لا يوجد مقطع يتم تشغيله.")
        
        await player.skip(force=True)
        await ctx.send("⏩ تم التخطي بنجاح.")

    @commands.command(name="volume", aliases=["vol"])
    @commands.check(check_chat)
    async def volume(self, ctx: commands.Context, vol: int):
        player = cast(wavelink.Player, ctx.guild.voice_client)
        if not player:
            return await ctx.send("❌ لا يوجد مشغل حالياً.")
        if vol < 0 or vol > 1000:
            return await ctx.send("❌ يرجى وضع رقم بين 0 و 1000")
        
        await player.set_volume(vol)
        await ctx.send(f"🔊 تم تغيير مستوى الصوت إلى: `{vol}%`")

    @commands.command(name="nowplaying", aliases=["np"])
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

    @commands.command(name="queue", aliases=["q"])
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

    @commands.command(name="clear")
    @commands.check(check_chat)
    async def clear_queue(self, ctx: commands.Context):
        player = cast(wavelink.Player, ctx.guild.voice_client)
        if not player:
            return await ctx.send("❌ لا يوجد مشغل حالياً.")
        
        player.queue.clear()
        await ctx.send("✅ تم حذف جميع المقاطع من القائمة.")

    @commands.command(name="pause")
    @commands.check(check_chat)
    async def pause(self, ctx: commands.Context):
        player = cast(wavelink.Player, ctx.guild.voice_client)
        if player and player.playing and not player.paused:
            await player.pause(True)
            await ctx.send("⏸️ تم الإيقاف المؤقت.")

    @commands.command(name="resume")
    @commands.check(check_chat)
    async def resume(self, ctx: commands.Context):
        player = cast(wavelink.Player, ctx.guild.voice_client)
        if player and player.paused:
            await player.pause(False)
            await ctx.send("▶️ تم استكمال التشغيل.")

    @commands.command(name="autoplay", aliases=["ap"])
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

    @commands.command(name="loop")
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

    @commands.command(name="filters")
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

    @commands.command(name="search")
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

    @commands.command(name="shuffle")
    @commands.check(check_chat)
    async def shuffle(self, ctx: commands.Context):
        player = cast(wavelink.Player, ctx.guild.voice_client)
        if not player or player.queue.is_empty:
            return await ctx.send("❌ القائمة فارغة حالياً.")
            
        player.queue.shuffle()
        await ctx.send("🔀 تم خلط القائمة بنجاح.")

async def setup(bot):
    await bot.add_cog(MusicCog(bot))
