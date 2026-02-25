import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
import threading
import os
import json
import random
from datetime import datetime

# ================= CONFIG =================

TOKEN = os.getenv("DISCORD_TOKEN")
FORUM_CHANNEL_ID = int(os.getenv("FORUM_CHANNEL_ID"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))
ROLE_ID = int(os.getenv("ROLE_ID"))
ADMIN_ROLE_ID = int(os.getenv("ADMIN_ROLE_ID"))

PHRASES_FILE = "phrases.json"
DATA_FILE = "data.json"

# ================= FLASK (ANTI SLEEP) =================

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive!"

def run_flask():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run_flask).start()

# ================= BOT =================

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ================= JSON UTILS =================

def load_json(file, default):
    if not os.path.exists(file):
        with open(file, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=4)
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

phrases = load_json(PHRASES_FILE, {
    "approve": ["Одобрено. Добро пожаловать."],
    "reject": ["Отказано."],
    "greetings": ["Леночка уже тут~"]
})

data_store = load_json(DATA_FILE, {
    "stats": {
        "approved": 0,
        "rejected": 0
    }
})

# ================= LOG FUNCTION =================

async def send_log(guild, text):
    channel = guild.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(f"📌 {text}")

# ================= BUTTON VIEW =================

class ApplicationView(discord.ui.View):
    def __init__(self, author_id):
        super().__init__(timeout=None)
        self.author_id = author_id

    @discord.ui.button(label="Одобрить", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):

        if ADMIN_ROLE_ID not in [r.id for r in interaction.user.roles]:
            return await interaction.response.send_message("Нет прав.", ephemeral=True)

        guild = interaction.guild
        member = guild.get_member(self.author_id)
        role = guild.get_role(ROLE_ID)

        if member and role:
            await member.add_roles(role)

        data_store["stats"]["approved"] += 1
        save_json(DATA_FILE, data_store)

        await send_log(guild, f"{member} одобрен {interaction.user}")
        await interaction.channel.edit(locked=True)

        text = random.choice(phrases["approve"])
        await interaction.response.send_message(text)

    @discord.ui.button(label="Отклонить", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):

        if ADMIN_ROLE_ID not in [r.id for r in interaction.user.roles]:
            return await interaction.response.send_message("Нет прав.", ephemeral=True)

        data_store["stats"]["rejected"] += 1
        save_json(DATA_FILE, data_store)

        await send_log(interaction.guild, f"Заявка отклонена {interaction.user}")
        await interaction.channel.edit(locked=True)

        text = random.choice(phrases["reject"])
        await interaction.response.send_message(text)

# ================= EVENTS =================

@bot.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    await bot.process_commands(message)

    if message.channel.id == FORUM_CHANNEL_ID:
        thread = await message.create_thread(
            name=f"Заявка от {message.author}",
            auto_archive_duration=1440
        )

        view = ApplicationView(message.author.id)
        await thread.send(random.choice(phrases["greetings"]), view=view)

# ================= ADMIN PANEL =================

@tree.command(name="admin", description="Админ панель")
async def admin_panel(interaction: discord.Interaction):

    if ADMIN_ROLE_ID not in [r.id for r in interaction.user.roles]:
        return await interaction.response.send_message("Нет прав.", ephemeral=True)

    embed = discord.Embed(title="Админ панель")
    embed.add_field(name="Одобрено", value=data_store["stats"]["approved"])
    embed.add_field(name="Отклонено", value=data_store["stats"]["rejected"])
    embed.timestamp = datetime.utcnow()

    await interaction.response.send_message(embed=embed, ephemeral=True)

# ================= RUN =================

bot.run(TOKEN)
