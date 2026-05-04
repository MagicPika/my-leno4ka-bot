import discord
from discord.ext import commands
import os, asyncio, sqlite3, json, threading, random
from datetime import datetime
from flask import Flask, request, jsonify

# ================= CONFIG =================
TOKEN = os.getenv("DISCORD_TOKEN")
FORUM_CHANNEL_ID = 1458885875692732438
SECRET = "2122428Matros"

COLOR_WAIT = 0x85144b
COLOR_OK = 0x2ecc71
COLOR_NO = 0xe74c3c
COLOR_WORK = 0xf1c40f

# ================= EVIL SYSTEM =================
EVIL_ENABLED = True
EVIL_LEVEL = 20

def change_evil(val):
    global EVIL_LEVEL
    EVIL_LEVEL = max(0, min(100, EVIL_LEVEL + val))

def get_phrase(action):
    lvl = EVIL_LEVEL

    if action == "idle":
        if lvl < 30:
            return "Ребят, заявки висят..."
        elif lvl < 70:
            return "Вы вообще собираетесь их смотреть?"
        else:
            return "АЛЁ ВЫ ЧТО СЛЕПЫЕ? ЗАЯВКИ ВИСЯТ"

    if action == "take":
        return "Ну наконец-то" if lvl > 50 else "Взяли заявку 👍"

    if action == "ok":
        return "Одобрено" if lvl < 50 else "Ну хоть это сделали"

    if action == "no":
        return "Отказ" if lvl < 50 else "Следующий."

# ================= DB =================
conn = sqlite3.connect("db.sqlite3", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS apps(
thread_id INTEGER PRIMARY KEY,
user_id INTEGER,
message_id INTEGER,
name TEXT,
fields TEXT,
status TEXT,
taken_by TEXT,
logs TEXT,
created_at TEXT
)
""")
conn.commit()

# ================= BOT =================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= UTILS =================
def get_app(tid):
    cur.execute("SELECT * FROM apps WHERE thread_id=?", (tid,))
    row = cur.fetchone()
    if not row:
        return None
    keys = ["thread_id","user_id","message_id","name","fields","status","taken_by","logs","created_at"]
    return dict(zip(keys,row))

async def get_thread_safe(tid):
    ch = bot.get_channel(tid)
    if not ch:
        try:
            ch = await bot.fetch_channel(tid)
        except:
            return None
    return ch

def build_embed(app_data, user):
    fields = json.loads(app_data["fields"])
    logs = json.loads(app_data["logs"])

    embed = discord.Embed(
        title=f"📋 {app_data['name']}",
        description=f"Статус: {app_data['status']}",
        color=COLOR_WAIT,
        timestamp=datetime.utcnow()
    )

    try:
        embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
    except:
        pass

    embed.add_field(name="👤 Пользователь", value=f"<@{app_data['user_id']}>", inline=False)

    for f in fields:
        embed.add_field(name=f["name"], value=f["value"], inline=False)

    if app_data["taken_by"]:
        embed.add_field(name="👮 Взял", value=app_data["taken_by"], inline=False)

    if logs:
        embed.add_field(name="📜 История", value="\n".join(logs[-5:]), inline=False)

    return embed

# ================= CREATE =================
async def create_app(uid, name, fields):
    user = await bot.fetch_user(uid)

    logs = [f"Создана {datetime.utcnow().strftime('%H:%M')}"]

    forum = bot.get_channel(FORUM_CHANNEL_ID)
    data = await forum.create_thread(name=name, content="Новая заявка")
    thread = data.thread

    msg = await thread.send("⏳ Загрузка...")

    cur.execute("""
    INSERT INTO apps VALUES(?,?,?,?,?,?,?,?,?)
    """, (
        thread.id, uid, msg.id, name,
        json.dumps(fields),
        "Ожидает", None,
        json.dumps(logs),
        datetime.utcnow().isoformat()
    ))
    conn.commit()

    embed = build_embed(get_app(thread.id), user)
    await msg.edit(embed=embed, content=None)
    await thread.send(view=AppView(thread.id))

    # таймер злости
    async def timer():
        await asyncio.sleep(1800)
        app = get_app(thread.id)
        if app and app["status"] == "Ожидает":
            change_evil(10)
            if EVIL_ENABLED:
                await thread.send(get_phrase("idle"))

    bot.loop.create_task(timer())

# ================= ACTION =================
async def handle_action(tid, action, actor):
    app = get_app(tid)
    if not app:
        return

    user = await bot.fetch_user(app["user_id"])
    logs = json.loads(app["logs"])

    if action == "take":
        app["status"] = "В работе"
        app["taken_by"] = actor
        logs.append(f"Взял {actor}")
        change_evil(-5)

    elif action == "ok":
        app["status"] = "Одобрено"
        logs.append(f"Одобрил {actor}")
        change_evil(-10)

    elif action == "no":
        app["status"] = "Отклонено"
        logs.append(f"Отклонил {actor}")
        change_evil(-10)

    cur.execute("UPDATE apps SET status=?, taken_by=?, logs=? WHERE thread_id=?",
                (app["status"], app["taken_by"], json.dumps(logs), tid))
    conn.commit()

    thread = await get_thread_safe(tid)
    if not thread:
        return

    msg = None
    try:
        msg = await thread.fetch_message(app["message_id"])
    except:
        async for m in thread.history(limit=30):
            if m.id == app["message_id"]:
                msg = m
                break

    if not msg:
        return

    embed = build_embed(get_app(tid), user)

    if app["status"] == "Одобрено":
        embed.color = COLOR_OK
    elif app["status"] == "Отклонено":
        embed.color = COLOR_NO
    elif app["status"] == "В работе":
        embed.color = COLOR_WORK

    await msg.edit(embed=embed)

    if EVIL_ENABLED:
        await thread.send(get_phrase(action))

# ================= BUTTONS =================
class AppView(discord.ui.View):
    def __init__(self, tid):
        super().__init__(timeout=None)
        self.tid = tid

    @discord.ui.button(label="👮 Взять", style=discord.ButtonStyle.primary)
    async def take(self, i, b):
        await handle_action(self.tid, "take", i.user.mention)
        await i.response.send_message("Ок", ephemeral=True)

    @discord.ui.button(label="✅ Одобрить", style=discord.ButtonStyle.success)
    async def ok(self, i, b):
        await handle_action(self.tid, "ok", i.user.mention)
        await i.response.send_message("Ок", ephemeral=True)

    @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.danger)
    async def no(self, i, b):
        await handle_action(self.tid, "no", i.user.mention)
        await i.response.send_message("Ок", ephemeral=True)

# ================= COMMANDS =================
@bot.command()
async def злость(ctx, val: int=None):
    global EVIL_LEVEL
    if val is None:
        await ctx.send(f"Злость: {EVIL_LEVEL}")
    else:
        EVIL_LEVEL = max(0,min(100,val))
        await ctx.send(f"Установлено: {EVIL_LEVEL}")

@bot.command()
async def леночка(ctx, mode: str):
    global EVIL_ENABLED
    if mode == "on":
        EVIL_ENABLED = True
        await ctx.send("Злая Леночка включена 😈")
    else:
        EVIL_ENABLED = False
        await ctx.send("Леночка добрая 💕")

# ================= FLASK =================
app = Flask(__name__)

@app.route("/zayavka", methods=["POST"])
def zayavka():
    if request.headers.get("Authorization") != f"Bearer {SECRET}":
        return jsonify({"error":"bad"}),401

    data = request.json
    bot.loop.create_task(create_app(
        int(data["discordId"]),
        data.get("authorName","Без имени"),
        data.get("fields",[])
    ))

    return jsonify({"ok":True})

def run():
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run).start()

# ================= RUN =================
bot.run(TOKEN)
