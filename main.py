import discord
from discord.ext import commands
from discord import app_commands
import os, asyncio, sqlite3, json, threading, random, time
from datetime import datetime
from flask import Flask, request, jsonify
from openai import OpenAI

# ================= CONFIG =================
TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

FORUM_CHANNEL_ID = 1458885875692732438   # форум заявок
MOD_ROLE_ID = 1457319043672576008        # роль модеров (для пинга)
CHAT_CHANNELS = [1457319047157911565]    # где Леночка общается

SECRET = "2122428Matros"

COLOR_WAIT = 0x85144b
COLOR_OK = 0x2ecc71
COLOR_NO = 0xe74c3c
COLOR_WORK = 0xf1c40f

# ================= GPT =================
client = OpenAI(api_key=OPENAI_API_KEY)
GPT_ENABLED = True

# ================= EVIL =================
EVIL_ENABLED = True
EVIL_LEVEL = 20

def change_evil(v):
    global EVIL_LEVEL
    EVIL_LEVEL = max(0, min(100, EVIL_LEVEL + v))

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

cur.execute("""
CREATE TABLE IF NOT EXISTS user_memory(
user_id INTEGER,
role TEXT,
content TEXT,
ts TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS user_stats(
user_id INTEGER PRIMARY KEY,
rep INTEGER DEFAULT 0
)
""")

conn.commit()

# ================= BOT =================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= MEMORY =================
def save_message(uid, role, content):
    cur.execute("INSERT INTO user_memory VALUES(?,?,?,?)",
                (uid, role, content, datetime.utcnow().isoformat()))
    conn.commit()

def load_memory(uid, limit=6):
    cur.execute("""
    SELECT role, content FROM user_memory
    WHERE user_id=? ORDER BY ts DESC LIMIT ?
    """, (uid, limit))
    rows = cur.fetchall()
    rows.reverse()
    return [{"role": r[0], "content": r[1]} for r in rows]

def get_rep(uid):
    cur.execute("SELECT rep FROM user_stats WHERE user_id=?", (uid,))
    row = cur.fetchone()
    return row[0] if row else 0

def update_rep(uid, delta):
    cur.execute("""
    INSERT INTO user_stats(user_id, rep)
    VALUES(?,?)
    ON CONFLICT(user_id)
    DO UPDATE SET rep = rep + ?
    """, (uid, delta, delta))
    conn.commit()

# ================= PERSONA =================
def persona(uid):
    rep = get_rep(uid)

    if EVIL_LEVEL < 30:
        mood = "добрая"
    elif EVIL_LEVEL < 70:
        mood = "строгая"
    else:
        mood = "злая"

    if rep > 5:
        att = "уважительно"
    elif rep < -5:
        att = "раздражённо"
    else:
        att = "нейтрально"

    return f"""
Ты Леночка, администратор Discord сервера армии.
Характер: {mood}
Отношение: {att}

Пиши коротко (1-2 предложения), как человек.
"""

# ================= GPT =================
async def lena_reply(uid, text):
    try:
        msgs = [
            {"role": "system", "content": persona(uid)},
            *load_memory(uid),
            {"role": "user", "content": text}
        ]

        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=msgs,
            max_tokens=120
        )

        ans = r.choices[0].message.content

        save_message(uid, "user", text)
        save_message(uid, "assistant", ans)

        if "спасибо" in text.lower():
            update_rep(uid, 1)

        return ans

    except Exception as e:
        print("GPT ERROR:", e)
        return None

# ================= UTILS =================
def get_app(tid):
    cur.execute("SELECT * FROM apps WHERE thread_id=?", (tid,))
    row = cur.fetchone()
    if not row:
        return None
    keys = ["thread_id","user_id","message_id","name","fields","status","taken_by","logs","created_at"]
    return dict(zip(keys,row))

async def get_thread(tid):
    ch = bot.get_channel(tid)
    if not ch:
        try:
            ch = await bot.fetch_channel(tid)
        except:
            return None
    return ch

# ================= EMBED =================
def build_embed(app, user):
    emb = discord.Embed(
        title=f"📋 {app['name']}",
        description=f"Статус: {app['status']}",
        color=COLOR_WAIT,
        timestamp=datetime.utcnow()
    )

    try:
        emb.set_thumbnail(url=user.display_avatar.url)
    except:
        pass

    emb.add_field(name="Пользователь", value=f"<@{app['user_id']}>", inline=False)

    for f in json.loads(app["fields"]):
        emb.add_field(name=f["name"], value=f["value"], inline=False)

    if app["taken_by"]:
        emb.add_field(name="Взял", value=app["taken_by"], inline=False)

    return emb

# ================= ACTION =================
async def handle_action(tid, action, actor, actor_id):
    app = get_app(tid)
    if not app:
        return

    user = await bot.fetch_user(app["user_id"])

    if action == "take":
        app["status"] = "В работе"
        app["taken_by"] = actor
        change_evil(-5)

    elif action == "ok":
        app["status"] = "Одобрено"
        change_evil(-10)

    elif action == "no":
        app["status"] = "Отклонено"
        change_evil(-10)

    cur.execute("UPDATE apps SET status=?, taken_by=? WHERE thread_id=?",
                (app["status"], app["taken_by"], tid))
    conn.commit()

    thread = await get_thread(tid)
    if not thread:
        return

    try:
        msg = await thread.fetch_message(app["message_id"])
    except:
        return

    emb = build_embed(get_app(tid), user)

    if app["status"] == "Одобрено":
        emb.color = COLOR_OK
    elif app["status"] == "Отклонено":
        emb.color = COLOR_NO
    elif app["status"] == "В работе":
        emb.color = COLOR_WORK

    await msg.edit(embed=emb)

    # ЛС пользователю
    try:
        await user.send(f"Ваша заявка: {app['status']}")
    except:
        pass

# ================= BUTTONS =================
class AppView(discord.ui.View):
    def __init__(self, tid):
        super().__init__(timeout=None)
        self.tid = tid

    @discord.ui.button(label="👮 Взять", style=discord.ButtonStyle.primary)
    async def take(self, i, b):
        await handle_action(self.tid, "take", i.user.mention, i.user.id)
        await i.response.send_message("Ок", ephemeral=True)

    @discord.ui.button(label="✅ Одобрить", style=discord.ButtonStyle.success)
    async def ok(self, i, b):
        await handle_action(self.tid, "ok", i.user.mention, i.user.id)
        await i.response.send_message("Ок", ephemeral=True)

    @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.danger)
    async def no(self, i, b):
        await handle_action(self.tid, "no", i.user.mention, i.user.id)
        await i.response.send_message("Ок", ephemeral=True)

# ================= CREATE =================
async def create_app(uid, name, fields):
    forum = bot.get_channel(FORUM_CHANNEL_ID)
    data = await forum.create_thread(name=name, content="Новая заявка")
    thread = data.thread

    msg = await thread.send("⏳")

    cur.execute("INSERT INTO apps VALUES(?,?,?,?,?,?,?,?,?)",
                (thread.id, uid, msg.id, name,
                 json.dumps(fields), "Ожидает", None, json.dumps([]),
                 datetime.utcnow().isoformat()))
    conn.commit()

    user = await bot.fetch_user(uid)
    await msg.edit(embed=build_embed(get_app(thread.id), user))
    await thread.send(view=AppView(thread.id))

    # напоминание
    async def timer():
        await asyncio.sleep(1800)
        app = get_app(thread.id)
        if app and app["status"] == "Ожидает":
            change_evil(10)
            await thread.send(f"<@&{MOD_ROLE_ID}> возьмите заявку")

    bot.loop.create_task(timer())

# ================= GPT CHAT =================
COOLDOWN = {}

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if GPT_ENABLED and message.channel.id in CHAT_CHANNELS:

        now = time.time()
        if now - COOLDOWN.get(message.author.id, 0) > 20:

            if bot.user in message.mentions or random.random() < 0.15:
                COOLDOWN[message.author.id] = now

                reply = await lena_reply(message.author.id, message.content)
                if reply:
                    await message.reply(reply)

    await bot.process_commands(message)

# ================= SLASH =================
@bot.tree.command(name="гпт")
async def gpt_toggle(interaction: discord.Interaction, mode: str):
    global GPT_ENABLED
    GPT_ENABLED = (mode == "on")
    await interaction.response.send_message(f"GPT: {mode}", ephemeral=True)

@bot.tree.command(name="злость")
async def evil_cmd(interaction: discord.Interaction, val: int=None):
    global EVIL_LEVEL
    if val is None:
        await interaction.response.send_message(f"{EVIL_LEVEL}", ephemeral=True)
    else:
        EVIL_LEVEL = val
        await interaction.response.send_message("Ок", ephemeral=True)

# ================= READY =================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print("READY")

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
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

threading.Thread(target=run).start()

bot.run(TOKEN)
