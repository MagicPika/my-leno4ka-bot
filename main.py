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

# ================= РЕПЛИКИ =================
РОФЛ_ПОЛУЧЕНО = [
    "Ооо, свеженькая заявОчка~ 💕 Леночка уже несёт наверх!",
    "Привет~ Я увидела твою анкету 💌 Сейчас покажу боссам",
    "Заявка получена 😌 Леночка держит её под контролем",
]

РОФЛ_ОДОБРЕНО = [
    "Урааа~ 💕 Тебя приняли!",
    "Боссы сказали ДА 😘",
    "Одобрено~ Леночка довольна 💖",
]

РОФЛ_ОТКЛОНЕНО = [
    "Ой… отказ 😔",
    "В этот раз не получилось…",
    "Боссы сказали нет 😈",
]

РОФЛ_УТОЧНИТЬ = [
    "Нужно уточнение 📞",
    "Допиши подробнее 💕",
]

РОФЛ_ОБЩЕНИЕ = [
    "Ммм? 💅",
    "Слушаю 👀",
    "Говори~",
]

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
npc = {"users": {}}

def load():
    global npc
    try:
        with open(NPC_FILE) as f:
            npc = json.load(f)
    except:
        pass

def save():
    with open(NPC_FILE, "w") as f:
        json.dump(npc, f)

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
        await self.user.send(random.choice(РОФЛ_ОДОБРЕНО))
        await interaction.response.send_message("Одобрено", ephemeral=True)

    @discord.ui.button(label="❌ Отказать", style=discord.ButtonStyle.danger)
    async def no(self, interaction, button):
        await self.user.send(random.choice(РОФЛ_ОТКЛОНЕНО))
        await interaction.response.send_message("Отклонено", ephemeral=True)

    @discord.ui.button(label="📞 Уточнить", style=discord.ButtonStyle.secondary)
    async def call(self, interaction, button):
        await self.user.send(random.choice(РОФЛ_УТОЧНИТЬ))
        await interaction.response.send_message("Запрошено уточнение", ephemeral=True)

# ================= ЗАЯВКА =================
async def process_app(uid, name, fields):
    user = await bot.fetch_user(uid)

    embed = discord.Embed(
        title=f"Заявка — {name}",
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

    await thread.thread.send("Новая заявка 👀")
    await thread.thread.send(view=AppView(user))

    # ЛС
    try:
        await user.send(random.choice(РОФЛ_ПОЛУЧЕНО))
    except:
        pass

# ================= NPC =================
def is_app_channel(channel):
    return isinstance(channel, discord.Thread)

def npc_reply(uid, text):
    rep = get_user(uid)["rep"]

    if "привет" in text:
        return "Приветик~ 💕" if rep >= 1 else "Привет"

    if rep <= -2:
        return "Я с тобой не разговариваю 😈"

    return random.choice(РОФЛ_ОБЩЕНИЕ)

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
    print(f"Леночка онлайн → {bot.user}")
    load()

# ================= FLASK =================
def run():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=run).start()

# ================= START =================
bot.run(TOKEN)
