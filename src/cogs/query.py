import discord
from discord.ext import commands
from discord import app_commands
from discord.app_commands import Choice
from langserve import RemoteRunnable
import requests

# Use `Choice` to show available PDF docs

class Agent(commands.Cog):
  def __init__(self, bot: commands.Bot) -> None:
    self.bot = bot

  @app_commands.command(name="query", description="Ask a question to the bot.")
  @app_commands.describe(query="Your question.")
  async def query(self, interaction: discord.Interaction, query: str) -> str:
    """ /query <query> """
    print("Query", query)
    await interaction.response.defer()
    res = requests.post("http://localhost:8000/agent", json={
      "input": query
    })
    print("Response", res.content.decode("utf-8"))
    print("Type", type(res.content.decode("utf-8")))
    await interaction.edit_original_response(content=res.content.decode("utf-8"))


async def setup(bot):
  await bot.add_cog(Agent(bot))