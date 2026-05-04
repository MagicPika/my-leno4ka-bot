import discord
from discord.ext import commands
from discord import app_commands
import os, asyncio, sqlite3, json, threading, random, time
from datetime import datetime
from flask import Flask, request, jsonify
from openai import OpenAI

# ================= CONFIG =================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

FORUM_CHANNEL_ID = 1458885875692732438   # форум заявок
MOD_ROLE_ID = 1457319043672576008        # роль модеров
CHAT_CHANNELS = [1457319047157911565]    # каналы общения

SECRET = "2122428Matros"

COLOR_WAIT = 0x85144b
COLOR_OK = 0x2ecc71
COLOR_NO = 0xe74c3c
COLOR_WORK = 0xf1c40f

# ================= OPENROUTER =================
client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

MODELS = [
    "openrouter/auto",
    "mistralai/mistral-7b-instruct:free"
]

GPT_ENABLED = True
CACHE = {}

# ================= DIALOG =================
DIALOGS = {}
DIALOG_TIMEOUT = 60

def start_dialog(uid):
    DIALOGS[uid] = time.time()

def in_dialog(uid):
    if uid not in DIALOGS:
        return False
    if time.time() - DIALOGS[uid] > DIALOG_TIMEOUT:
        del DIALOGS[uid]
        return False
    return True

def refresh_dialog(uid):
    DIALOGS[uid] = time.time()

# ================= TRIGGERS =================
TRIGGERS = ["леночка", "лена", "лен"]
COMMAND_WORDS = ["помоги", "что делать", "как вступить", "объясни"]

def is_lena_call(text):
    t = text.lower()
    return any(x in t for x in TRIGGERS) or any(x in t for x in COMMAND_WORDS)

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

conn.commit()

# ================= MEMORY =================
def save_message(uid, role, content):
    cur.execute("INSERT INTO user_memory VALUES(?,?,?,?)",
                (uid, role, content, datetime.utcnow().isoformat()))
    conn.commit()

def load_memory(uid):
    cur.execute("SELECT role, content FROM user_memory WHERE user_id=? ORDER BY ts DESC LIMIT 6", (uid,))
    rows = cur.fetchall()
    rows.reverse()
    return [{"role": r[0], "content": r[1]} for r in rows]

# ================= PERSONA =================
def persona():
    return """
Ты Леночка, живой человек.
Отвечай ТОЛЬКО на русском.
Коротко (1-2 предложения).
Можешь быть с характером.
Поддерживай диалог.
"""

# ================= GPT =================
def fallback(text):
    return random.choice([
        "Ты сейчас серьёзно?",
        "Заявку открой",
        "Сам подумай"
    ])

async def lena_reply(uid, text):
    key = text.lower()

    if key in CACHE:
        return CACHE[key]

    messages = [
        {"role": "system", "content": persona()},
        *load_memory(uid),
        {"role": "user", "content": text}
    ]

    for model in MODELS:
        try:
            r = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=120
            )

            ans = r.choices[0].message.content
            print("GPT:", ans)

            if ans:
                save_message(uid, "user", text)
                save_message(uid, "assistant", ans)
                CACHE[key] = ans
                return ans

        except Exception as e:
            print("MODEL FAIL:", e)

    return fallback(text)

# ================= BOT =================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= EMBED =================
def build_embed(app, user):
    emb = discord.Embed(
        title=f"📋 {app['name']}",
        description=f"Статус: {app['status']}",
        timestamp=datetime.utcnow()
    )
    emb.set_thumbnail(url=user.display_avatar.url)

    for f in json.loads(app["fields"]):
        emb.add_field(name=f["name"], value=f["value"], inline=False)

    return emb

# ================= ACTION =================
def get_app(tid):
    cur.execute("SELECT * FROM apps WHERE thread_id=?", (tid,))
    row = cur.fetchone()
    if not row:
        return None
    keys = ["thread_id","user_id","message_id","name","fields","status","taken_by","logs","created_at"]
    return dict(zip(keys,row))

async def handle_action(tid, action, actor):
    app = get_app(tid)
    if not app:
        return

    if action == "take":
        app["status"] = "В работе"
    elif action == "ok":
        app["status"] = "Одобрено"
    elif action == "no":
        app["status"] = "Отклонено"

    cur.execute("UPDATE apps SET status=? WHERE thread_id=?", (app["status"], tid))
    conn.commit()

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

# ================= CREATE APP =================
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

# ================= CHAT =================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if GPT_ENABLED and message.channel.id in CHAT_CHANNELS:

        uid = message.author.id
        text = message.content

        called = bot.user in message.mentions or is_lena_call(text)
        active = in_dialog(uid)

        if called:
            start_dialog(uid)

        if called or active:
            refresh_dialog(uid)
            reply = await lena_reply(uid, text)
            await message.reply(reply)

    await bot.process_commands(message)

# ================= COMMAND =================
@bot.tree.command(name="гпт")
async def gpt_toggle(interaction: discord.Interaction, mode: str):
    global GPT_ENABLED
    GPT_ENABLED = (mode == "on")
    await interaction.response.send_message("OK", ephemeral=True)

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

bot.run(DISCORD_TOKEN)
