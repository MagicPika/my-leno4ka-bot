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

FORUM_CHANNEL_ID = 1458885875692732438
MOD_ROLE_ID = 1457319043672576008
CHAT_CHANNELS = [1457319047157911565]

SECRET = "2122428Matros"

OVERDUE_MINUTES = 10
REMIND_MINUTES = 5

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
    "x-ai/grok-3-mini-beta",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-27b-it:free"
]

# ================= DB =================
conn = sqlite3.connect("db.sqlite3", check_same_thread=False)
cur = conn.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS apps(
thread_id INTEGER PRIMARY KEY,
user_id INTEGER,
message_id INTEGER,
name TEXT,
fields TEXT,
status TEXT,
taken_by TEXT,
created_at TEXT
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS user_memory(
user_id INTEGER,
role TEXT,
content TEXT,
ts TEXT
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS mod_stats(
user TEXT PRIMARY KEY,
taken INTEGER DEFAULT 0,
approved INTEGER DEFAULT 0,
rejected INTEGER DEFAULT 0
)""")

conn.commit()

# ================= MEMORY =================
def save_message(uid, role, content):
    cur.execute("INSERT INTO user_memory VALUES(?,?,?,?)",
                (uid, role, content, datetime.utcnow().isoformat()))
    conn.commit()

def load_memory(uid):
    cur.execute("SELECT role, content FROM user_memory WHERE user_id=? ORDER BY ts DESC LIMIT 6",(uid,))
    rows = cur.fetchall()
    rows.reverse()
    return [{"role":r[0],"content":r[1]} for r in rows]

# ================= PERSONA =================
def persona():
    return """
Ты Леночка, администратор Discord.

Правила:
- только русский язык
- коротко и по делу
- можешь быть резкой
- не пиши как ИИ
"""

# ================= ФИЛЬТРЫ =================
def is_english(text):
    return any(c in text.lower() for c in "abcdefghijklmnopqrstuvwxyz")

BAD_PHRASES = ["i am an ai","as an ai","i cannot","i'm sorry"]

def is_bad(text):
    t = text.lower()
    return any(x in t for x in BAD_PHRASES)

# ================= ТУПЫЕ ВОПРОСЫ =================
STUPID_REPLIES = [
    "Ты нормально сформулировать можешь?",
    "Я не телепат",
    "Конкретнее давай",
    "Это вопрос вообще?",
    "Соберись и напиши нормально"
]

def is_stupid(text):
    t = text.strip().lower()
    if len(t) <= 3: return True
    if len(t.split()) == 1: return True
    if t.count("?") >= 3: return True
    return False

# ================= GPT =================
async def lena_reply(uid, text):
    messages = [
        {"role":"system","content":persona()},
        *load_memory(uid),
        {"role":"user","content":text}
    ]

    for model in MODELS:
        try:
            r = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=120
            )

            ans = r.choices[0].message.content

            if not ans: continue
            if is_english(ans): continue
            if is_bad(ans): continue

            save_message(uid,"user",text)
            save_message(uid,"assistant",ans)
            return ans

        except Exception as e:
            print("GPT FAIL:", e)

    return "Нормально напиши вопрос"

# ================= AI ЗАЯВКИ =================
async def ai_review(name, fields):
    text = "\n".join([f"{f['name']}: {f['value']}" for f in fields])

    try:
        r = client.chat.completions.create(
            model="x-ai/grok-3-mini-beta",
            messages=[
                {"role":"system","content":"Ответ JSON: {\"decision\":\"ok|no|review\",\"reason\":\"...\"}"},
                {"role":"user","content":text}
            ],
            max_tokens=120
        )

        data = json.loads(r.choices[0].message.content)
        d = data.get("decision","review")
        if d not in ["ok","no","review"]: d="review"
        return d, data.get("reason","-")

    except:
        return "review","ошибка"

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

    if app["taken_by"]:
        emb.add_field(name="Взял", value=app["taken_by"], inline=False)

    return emb

# ================= ACTION =================
def get_app(tid):
    cur.execute("SELECT * FROM apps WHERE thread_id=?", (tid,))
    row = cur.fetchone()
    if not row: return None
    keys=["thread_id","user_id","message_id","name","fields","status","taken_by","created_at"]
    return dict(zip(keys,row))

async def handle_action(tid, action, actor):
    app = get_app(tid)
    if not app: return

    if action=="take":
        app["status"]="В работе"
        app["taken_by"]=actor
    elif action=="ok":
        app["status"]="Одобрено"
    elif action=="no":
        app["status"]="Отклонено"

    cur.execute("UPDATE apps SET status=?,taken_by=? WHERE thread_id=?",
                (app["status"],app["taken_by"],tid))
    conn.commit()

    thread = bot.get_channel(tid)
    if not thread: return

    msg = await thread.fetch_message(app["message_id"])
    user = await bot.fetch_user(app["user_id"])

    await msg.edit(embed=build_embed(get_app(tid), user))

    try:
        await user.send(f"Заявка: {app['status']}")
    except: pass

# ================= BUTTONS =================
class AppView(discord.ui.View):
    def __init__(self, tid):
        super().__init__(timeout=None)
        self.tid = tid

    @discord.ui.button(label="👮 Взять", style=discord.ButtonStyle.primary)
    async def take(self, i, b):
        await handle_action(self.tid, "take", i.user.mention)
        await i.response.send_message("OK", ephemeral=True)

    @discord.ui.button(label="✅ Одобрить", style=discord.ButtonStyle.success)
    async def ok(self, i, b):
        await handle_action(self.tid, "ok", i.user.mention)
        await i.response.send_message("OK", ephemeral=True)

    @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.danger)
    async def no(self, i, b):
        await handle_action(self.tid, "no", i.user.mention)
        await i.response.send_message("OK", ephemeral=True)

# ================= CREATE =================
async def create_app(uid, name, fields):
    forum = bot.get_channel(FORUM_CHANNEL_ID)
    data = await forum.create_thread(name=name, content="Новая заявка")
    thread = data.thread

    msg = await thread.send("⏳")

    cur.execute("INSERT INTO apps VALUES(?,?,?,?,?,?,?,?)",
        (thread.id, uid, msg.id, name, json.dumps(fields), "Ожидает", None, datetime.utcnow().isoformat()))
    conn.commit()

    user = await bot.fetch_user(uid)
    await msg.edit(embed=build_embed(get_app(thread.id), user))
    await thread.send(view=AppView(thread.id))

    decision, reason = await ai_review(name, fields)
    await thread.send(f"🤖 AI: {decision}\n{reason}")

    if decision=="ok":
        await handle_action(thread.id, "ok", "AI")
    elif decision=="no":
        await handle_action(thread.id, "no", "AI")

# ================= BOT =================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_message(message):
    if message.author.bot: return

    if message.channel.id in CHAT_CHANNELS:
        if is_stupid(message.content):
            reply = random.choice(STUPID_REPLIES)
        else:
            reply = await lena_reply(message.author.id, message.content)

        await message.reply(reply)

    await bot.process_commands(message)

# ================= WEB =================
app = Flask(__name__)

@app.route("/")
def dash():
    cur.execute("SELECT name,status FROM apps")
    rows = cur.fetchall()
    return "<br>".join([f"{r[0]} — {r[1]}" for r in rows])

@app.route("/zayavka", methods=["POST"])
def zayavka():
    data = request.json
    bot.loop.create_task(create_app(
        int(data["discordId"]),
        data.get("authorName","Без имени"),
        data.get("fields",[])
    ))
    return {"ok":True}

def run():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

threading.Thread(target=run).start()

bot.run(DISCORD_TOKEN)
