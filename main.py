import discord
from discord.ext import commands
import os, random, asyncio, json, threading
from flask import Flask, request, jsonify

# ================= НАСТРОЙКИ =================
TOKEN = os.getenv("DISCORD_TOKEN")

FORUM_CHANNEL_ID = 1458885875692732438
SECRET = "2122428Matros"

ARMY_SITE = "https://your-site.ru"
ARMY_DISCORD = "https://discord.gg/yourinvite"

NPC_CHANNELS = []  # пусто = все каналы кроме заявок

# ================= ФРАЗЫ =================
РОФЛ_ПОЛУЧЕНО = [
    "Ооо, свеженькая заявОчка~ 💕",
    "Заявка получена, не пропадай 😌",
]

РОФЛ_ОДОБРЕНО = [
    "Ты принят 💕",
    "Добро пожаловать 😘",
]

РОФЛ_ОТКЛОНЕНО = [
    "Отказ 😔",
    "В этот раз нет…",
]

РОФЛ_УТОЧНИТЬ = [
    "Нужно уточнение 📞",
    "Напиши подробнее",
]

РОФЛ_ОБЩЕНИЕ = [
    "Ммм?",
    "Слушаю",
    "Говори~",
]

# ================= FLASK =================
app = Flask(__name__)

@app.route("/zayavka", methods=["POST"])
def zayavka():
    if request.headers.get("Authorization") != f"Bearer {SECRET}":
        return jsonify({"error": "bad key"}), 401

    data = request.json
    uid = int(data["discordId"])
    name = data.get("authorName", "Без имени")
    fields = data.get("fields", [])

    bot.loop.create_task(process_app(uid, name, fields))
    return jsonify({"ok": True})

# ================= БОТ =================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= МЕНЮ =================
class ArmyMenuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

        self.add_item(discord.ui.Button(label="🌐 Сайт", url=ARMY_SITE))
        self.add_item(discord.ui.Button(label="💬 Discord", url=ARMY_DISCORD))

    @discord.ui.button(label="📜 Устав", style=discord.ButtonStyle.primary)
    async def rules(self, interaction, button):
        await interaction.response.send_message(
            "📜 Соблюдай дисциплину и приказы.",
            ephemeral=True
        )

    @discord.ui.button(label="🎯 Требования", style=discord.ButtonStyle.secondary)
    async def req(self, interaction, button):
        await interaction.response.send_message(
            "🎯 16+ | Адекватность | Онлайн",
            ephemeral=True
        )

# ================= КНОПКИ ЗАЯВКИ =================
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
        await interaction.response.send_message("Уточнение", ephemeral=True)

# ================= ЗАЯВКА =================
async def process_app(uid, name, fields):
    user = await bot.fetch_user(uid)

    embed = discord.Embed(
        title=f"Заявка — {name}",
        description=f"🌐 {ARMY_SITE}\n💬 {ARMY_DISCORD}",
        color=0xff69b4
    )

    embed.add_field(name="Пользователь", value=f"<@{uid}>", inline=False)

    for f in fields:
        embed.add_field(name=f["name"], value=f["value"], inline=False)

    forum = bot.get_channel(FORUM_CHANNEL_ID)

    thread = await forum.create_thread(
        name=name,
        embed=embed
    )

    await thread.thread.send("Новая заявка 👀", view=ArmyMenuView())
    await thread.thread.send(view=AppView(user))

    try:
        await user.send(random.choice(РОФЛ_ПОЛУЧЕНО))
    except:
        pass

# ================= NPC =================
def is_app_channel(channel):
    return isinstance(channel, discord.Thread)

def npc_reply(text):
    t = text.lower()

    if any(x in t for x in ["сайт"]):
        return ("🌐 Вот сайт армии", "links")

    if any(x in t for x in ["дискорд", "discord"]):
        return ("💬 Вот Discord", "links")

    if any(x in t for x in ["меню", "помощь", "полезное"]):
        return ("📌 Вот всё полезное", "menu")

    return (random.choice(РОФЛ_ОБЩЕНИЕ), None)

# ================= MESSAGE =================
@bot.event
async def on_message(msg):
    if msg.author.bot:
        return

    if is_app_channel(msg.channel):
        return

    if NPC_CHANNELS and msg.channel.id not in NPC_CHANNELS:
        return

    if "леночка" in msg.content.lower():
        text, mode = npc_reply(msg.content)

        if mode == "menu":
            await msg.reply(text, view=ArmyMenuView())
        elif mode == "links":
            await msg.reply(text, view=ArmyMenuView())
        else:
            await msg.reply(text)

    await bot.process_commands(msg)

# ================= КОМАНДА =================
@bot.command()
async def меню(ctx):
    await ctx.send("📌 Меню армии", view=ArmyMenuView())

# ================= READY =================
@bot.event
async def on_ready():
    print(f"Леночка онлайн → {bot.user}")

# ================= FLASK =================
def run():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=run).start()

# ================= СТАРТ =================
bot.run(TOKEN)
