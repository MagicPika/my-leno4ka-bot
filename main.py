import discord
from discord.ext import commands
import os, random, asyncio, threading
from flask import Flask, request, jsonify

# ================= НАСТРОЙКИ =================
TOKEN = os.getenv("DISCORD_TOKEN")
SECRET = "2122428Matros"

FORUM_CHANNEL_ID = 1458885875692732438
REVIEWER_ROLE_ID = 1457319043672576008

РОЛЬ_НА_ПРОВЕРКЕ = 1474320899598581791
РОЛЬ_ОДОБРЕНО = 1457319043315929267

# ================= СОСТОЯНИЕ =================
applications = {}       # user_id -> данные
active_applications = set()
application_meta = {}   # уровни злости
npc_memory = {}         # память леночки

# ================= РОФЛЫ =================
РОФЛ_ПОЛУЧЕНО = [
    "Ооо~ заявочка пришла 💕",
    "Леночка приняла заявку и уже несёт наверх~"
]

РОФЛ_ОДОБРЕНО = ["Добро пожаловать 💕"]
РОФЛ_ОТКЛОНЕНО = ["Отказ 😔"]

# ================= ЗЛАЯ ЛЕНОЧКА =================
ЛЕНОЧКА_ЗЛАЯ = {
    0: ["Заявочка лежит… 💅"],
    1: ["Заявка уже висит 👀"],
    2: ["Кто игнорит заявки?"],
    3: ["Леночка злится 😠"],
    4: ["ВСЁ. Это уже бардак"]
}

# ================= БОТ =================
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= FLASK =================
app = Flask(__name__)

@app.route("/zayavka", methods=["POST"])
def zayavka():
    if request.headers.get("Authorization") != f"Bearer {SECRET}":
        return jsonify({"error": "bad key"}), 401

    data = request.json
    discord_id = int(data["discordId"])
    author_name = data.get("authorName", "Без имени")
    fields = data.get("fields", [])

    bot.loop.create_task(обработать_заявку(discord_id, author_name, fields))
    return {"ok": True}

# ================= NPC =================
def get_npc(uid):
    if uid not in npc_memory:
        npc_memory[uid] = {"rep": 0}
    return npc_memory[uid]

def npc_phrase(uid, type_):
    rep = get_npc(uid)["rep"]

    if type_ == "take":
        return "О, работаешь 😌" if rep >= 0 else "Ну наконец-то"
    if type_ == "ignore":
        return "Ты игноришь 😈" if rep < 0 else "Не тяни"
    if type_ == "approve":
        return "Вот это хорошо 💕"
    return ""

# ================= УРОВЕНЬ ЗЛОСТИ =================
def get_level(uid):
    meta = application_meta.get(uid)
    if not meta:
        return 0

    t = asyncio.get_event_loop().time() - meta["time"]

    if t > 7200: return 4
    if t > 3600: return 3
    if t > 1800: return 2
    if t > 600: return 1
    return 0

# ================= КНОПКИ =================
class View(discord.ui.View):
    def __init__(self, user, thread, msg):
        super().__init__(timeout=None)
        self.user = user
        self.thread = thread
        self.msg = msg
        self.owner = None

    async def update(self, status, reviewer=None):
        emb = self.msg.embeds[0]
        emb.set_field_at(0, name="Статус", value=status)
        if reviewer:
            emb.set_footer(text=f"Ответственный: {reviewer}")
        await self.msg.edit(embed=emb)

    @discord.ui.button(label="👤 Взять", style=discord.ButtonStyle.primary)
    async def take(self, i: discord.Interaction, _):
        self.owner = i.user.id
        applications[self.user.id]["status"] = "В работе"
        applications[self.user.id]["reviewer"] = i.user.id

        get_npc(i.user.id)["rep"] += 1

        await i.response.send_message("Взял", ephemeral=True)
        await self.update("🟡 В работе", i.user)

    @discord.ui.button(label="🔁 Передать", style=discord.ButtonStyle.secondary)
    async def transfer(self, i, _):
        if self.owner != i.user.id:
            return await i.response.send_message("Не ты", ephemeral=True)

        self.owner = None
        applications[self.user.id]["reviewer"] = None

        await i.response.send_message("Передано", ephemeral=True)
        await self.update("🟣 Ожидает")

    @discord.ui.button(label="✅", style=discord.ButtonStyle.success)
    async def approve(self, i, _):
        member = i.guild.get_member(self.user.id)

        if member:
            role = i.guild.get_role(РОЛЬ_ОДОБРЕНО)
            if role:
                await member.add_roles(role)

        await self.finish(i, "Одобрено", 0x2ecc71)

    @discord.ui.button(label="❌", style=discord.ButtonStyle.danger)
    async def decline(self, i, _):
        await self.finish(i, "Отклонено", 0xe74c3c)

    async def finish(self, i, text, color):
        for c in self.children:
            c.disabled = True

        emb = self.msg.embeds[0]
        emb.title = "Заявка закрыта"
        emb.description = text
        emb.color = color

        await self.msg.edit(embed=emb, view=self)

        await asyncio.sleep(2)
        await self.thread.edit(archived=True, locked=True)

        applications.pop(self.user.id, None)
        application_meta.pop(self.user.id, None)

# ================= ОБРАБОТКА =================
async def обработать_заявку(uid, name, fields):

    if uid in active_applications:
        return

    active_applications.add(uid)

    channel = bot.get_channel(FORUM_CHANNEL_ID)
    thread_data = await channel.create_thread(
        name=f"Заявка — {name}",
        content="📋 Новая заявка",
        auto_archive_duration=10080
    )

    thread = thread_data.thread

    guild = thread.guild
    try:
        member = await guild.fetch_member(uid)
    except:
        member = None

    if not member:
        await thread.send("❌ Не на сервере")
        await asyncio.sleep(2)
        await thread.edit(archived=True, locked=True)
        return

    user = await bot.fetch_user(uid)
    avatar = user.display_avatar.url

    embed = discord.Embed(title=f"Заявка {name}", color=0x85144b)
    embed.set_thumbnail(url=avatar)
    embed.add_field(name="Статус", value="🟣 Ожидает", inline=False)
    embed.add_field(name="Заявитель", value=f"<@{uid}>", inline=False)

    for f in fields:
        embed.add_field(name=f["name"], value=f["value"], inline=False)

    msg = await thread.send(embed=embed)
    await thread.send("Действия:", view=View(user, thread, msg))

    applications[uid] = {
        "thread_id": thread.id,
        "status": "Ожидает",
        "reviewer": None
    }

    application_meta[uid] = {
        "time": asyncio.get_event_loop().time(),
        "level": 0
    }

    try:
        await user.send(random.choice(РОФЛ_ПОЛУЧЕНО))
    except:
        pass

# ================= SLA =================
async def watchdog():
    await bot.wait_until_ready()

    while True:
        for uid, data in applications.items():
            thread = bot.get_channel(data["thread_id"])
            if not thread or thread.archived:
                continue

            lvl = get_level(uid)
            old = application_meta[uid]["level"]

            if lvl > old:
                application_meta[uid]["level"] = lvl

                txt = random.choice(ЛЕНОЧКА_ЗЛАЯ[lvl])
                reviewer = data["reviewer"]

                if reviewer:
                    txt += f"\n👉 <@{reviewer}>"
                else:
                    txt += f"\n👉 <@&{REVIEWER_ROLE_ID}>"

                await thread.send(txt)

        await asyncio.sleep(600)

# ================= ПАНЕЛЬ =================
@bot.command()
async def панель(ctx):
    emb = discord.Embed(title="Панель заявок")

    for uid, data in applications.items():
        emb.add_field(
            name=f"<@{uid}>",
            value=f"{data['status']}",
            inline=False
        )

    await ctx.send(embed=emb)

# ================= ЗАПУСК =================
def run():
    app.run("0.0.0.0", port=10000)

threading.Thread(target=run).start()

@bot.event
async def on_ready():
    print("Бот запущен")
    bot.loop.create_task(watchdog())

bot.run(TOKEN)
