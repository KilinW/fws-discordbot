import asyncio
import discord
from discord.ext import commands
from typing import Optional, Literal
import os

# Add parent directory to path
cog_dir = os.path.dirname(os.path.realpath(__file__))

class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.description = '''A cog for admin commands. Including reload, sync, etc.'''

    @commands.command(name="reload")
    @commands.is_owner()
    async def reload(self, ctx: commands.Context):
        for filename in os.listdir(cog_dir):
            if not filename.endswith(".py"):
                continue
            try:
                await self.bot.reload_extension(f"cogs.{filename[:-3]}")
                await ctx.send(f"{filename[:-3]} is reloaded.")
            except commands.ExtensionNotLoaded:
                await ctx.send(f"{filename[:-3]} is not loaded.")
                await self.bot.load_extension(f"cogs.{filename[:-3]}")
            except commands.ExtensionNotFound:
                await ctx.send(f"{filename[:-3]} is not found.")
            except commands.NoEntryPointError:
                await ctx.send(f"{filename[:-3]} has no setup function.")
            except commands.ExtensionFailed:
                await ctx.send(f"{filename[:-3]} had an execution error.")
        loaded_cogs = [f"\r- **{name}**:\r {cog.description}" for name, cog in self.bot.cogs.items()]
        loaded_cogs_str = "".join(loaded_cogs)
        await ctx.send(f"# Current loaded cogs:{loaded_cogs_str}")

    @commands.command(name="sync")
    @commands.is_owner()
    async def sync(
        self,
        ctx: commands.Context,
        guilds: commands.Greedy[discord.Object],
        spec: Optional[Literal["~", "*", "^"]] = None,
    ) -> None:
        synced = []
        if not guilds:
            if spec == "~":             # This will sync all guild commands for the current context’s guild.
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":           # This command copies all global commands to the current guild (within the CommandTree) and syncs.
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":           # This command will remove all guild commands from the CommandTree and syncs, which effectively removes all commands from the guild.
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []             # This command will sync the 3 guild ids we passed: 123, 456 and 789. Only their guilds and guild-bound commands.
            else:                       # Take all global commands and send them to Discord.
                synced = await ctx.bot.tree.sync()

            await ctx.send(
                f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
            )

            return

        ret = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                ret += 1

        # Send all command that was synced
        await ctx.send(f"Synced commands to {ret}/{len(guilds)}.")

async def setup(bot):
    await bot.add_cog(Admin(bot))