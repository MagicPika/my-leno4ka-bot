import discord
from discord.ext import commands
import os, random, asyncio, json, threading
from flask import Flask, request, jsonify

# ================= НАСТРОЙКИ =================
TOKEN = os.getenv("DISCORD_TOKEN")

FORUM_CHANNEL_ID = 1458885875692732438
SECRET = "2122428Matros"

ROLE_CHECK = 1474320899598581791
ROLE_APPROVED = 1457319043315929267

NPC_CHANNELS = []  # если пусто → все каналы кроме заявок

NPC_FILE = "npc.json"

# ================= FLASK =================
app = Flask(__name__)

@app.route("/zayavka", methods=["POST"])
def zayavka():
    if request.headers.get("Authorization") != f"Bearer {SECRET}":
        return jsonify({"error": "bad key"}), 401

    data = request.json
    discord_id = int(data["discordId"])
    author = data.get("authorName", "Без имени")
    fields = data.get("fields", [])

    bot.loop.create_task(process_app(discord_id, author, fields))
    return jsonify({"ok": True})

# ================= NPC =================
npc = {
    "users": {},
    "mood": 0,
    "energy": 5
}

def save():
    with open(NPC_FILE, "w") as f:
        json.dump(npc, f)

def load():
    global npc
    try:
        with open(NPC_FILE) as f:
            npc = json.load(f)
    except:
        pass

def get_user(uid):
    if str(uid) not in npc["users"]:
        npc["users"][str(uid)] = {"rep": 0}
    return npc["users"][str(uid)]

# ================= БОТ =================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= КНОПКИ =================
class AppView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=None)
        self.user = user

    @discord.ui.button(label="✅ Одобрить", style=discord.ButtonStyle.success)
    async def ok(self, interaction, button):
        await self.user.send("Твоя заявка одобрена 💕")
        await interaction.response.send_message("OK", ephemeral=True)

    @discord.ui.button(label="❌ Отказать", style=discord.ButtonStyle.danger)
    async def no(self, interaction, button):
        await self.user.send("Твоя заявка отклонена 😔")
        await interaction.response.send_message("NO", ephemeral=True)

# ================= ЗАЯВКА =================
async def process_app(uid, name, fields):
    user = await bot.fetch_user(uid)

    embed = discord.Embed(
        title=f"Заявка {name}",
        color=0xff69b4
    )

    embed.add_field(name="Пользователь", value=f"<@{uid}>", inline=False)

    for f in fields:
        embed.add_field(name=f["name"], value=f["value"], inline=False)

    channel = bot.get_channel(FORUM_CHANNEL_ID)

    thread = await channel.create_thread(
        name=f"{name}",
        embed=embed
    )

    await thread.thread.send("Новая заявка")
    await thread.thread.send(view=AppView(user))

# ================= NPC ЛОГИКА =================
def is_app_channel(channel):
    return isinstance(channel, discord.Thread)

def npc_reply(uid, text):
    rep = get_user(uid)["rep"]

    if "привет" in text:
        return "Привет 💕" if rep >= 1 else "Привет"

    if rep < -2:
        return "Не хочу с тобой говорить 😈"

    return random.choice(["Ммм?", "Слушаю", "Говори"])

# ================= MESSAGE =================
@bot.event
async def on_message(msg):
    if msg.author.bot:
        return

    # заявки не трогаем
    if is_app_channel(msg.channel):
        return

    # фильтр каналов
    if NPC_CHANNELS and msg.channel.id not in NPC_CHANNELS:
        return

    if "леночка" in msg.content.lower():
        reply = npc_reply(msg.author.id, msg.content.lower())
        await msg.reply(reply)

    await bot.process_commands(msg)

# ================= READY =================
@bot.event
async def on_ready():
    print("Бот запущен")
    load()

# ================= FLASK RUN =================
def run():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=run).start()

# ================= START =================
bot.run(TOKEN)
