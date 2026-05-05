import discord
from discord.ext import commands, tasks
from discord import app_commands
import os, asyncio, sqlite3, json, threading, random, time
from datetime import datetime, timedelta
from flask import Flask, request
from openai import OpenAI

# ================= CONFIG =================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

FORUM_CHANNEL_ID = 1458885875692732438
MOD_ROLE_ID = 1457319043672576008
CHAT_CHANNELS = [1457319047157911565]
SECRET = "2122428Matros"


BOSS_IDS = {
    924956705756971028,
    695943956856307744,
    550051551700451369
}

OVERDUE_MIN = 15
REMIND_MIN = 7

# ================= OPENROUTER =================
client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

MODEL = "x-ai/grok-3-mini-beta"

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
created_at TEXT,
last_update TEXT
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS reputation(
user_id INTEGER PRIMARY KEY,
score INTEGER DEFAULT 0
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS mod_stats(
user TEXT PRIMARY KEY,
taken INTEGER DEFAULT 0,
approved INTEGER DEFAULT 0,
rejected INTEGER DEFAULT 0
)""")

conn.commit()

# ================= HELPERS =================
def is_boss(uid):
    return uid in BOSS_IDS

def update_reputation(uid, delta):
    cur.execute("""
    INSERT INTO reputation(user_id,score)
    VALUES(?,?)
    ON CONFLICT(user_id) DO UPDATE SET score=score+?
    """,(uid,delta,delta))
    conn.commit()

def update_mod(user, action):
    cur.execute("""
    INSERT INTO mod_stats(user,taken,approved,rejected)
    VALUES(?,?,?,?)
    ON CONFLICT(user) DO UPDATE SET
    taken=taken+?,
    approved=approved+?,
    rejected=rejected+?
    """,(user,
         1 if action=="take" else 0,
         1 if action=="ok" else 0,
         1 if action=="no" else 0,
         1 if action=="take" else 0,
         1 if action=="ok" else 0,
         1 if action=="no" else 0))
    conn.commit()

# ================= MOOD =================
LENA_MOOD = {"state":"calm","last":0}

def update_mood():
    if time.time() - LENA_MOOD["last"] < 30:
        return LENA_MOOD["state"]

    LENA_MOOD["last"] = time.time()

    cur.execute("SELECT COUNT(*) FROM apps WHERE status='Ожидает'")
    pending = cur.fetchone()[0]

    if pending >= 5:
        LENA_MOOD["state"] = "angry"
    elif pending >= 2:
        LENA_MOOD["state"] = "tired"
    else:
        LENA_MOOD["state"] = "calm"

    return LENA_MOOD["state"]

# ================= GPT =================
def persona(uid):
    if is_boss(uid):
        return "Ты Леночка. Перед тобой начальство. Отвечай уважительно и чётко."

    mood = update_mood()
    if mood == "angry":
        return "Ты злая админша. Коротко и резко."
    elif mood == "tired":
        return "Ты уставшая админша. Коротко."
    return "Ты спокойная админша."

async def lena_reply(uid, text):
    try:
        r = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role":"system","content":persona(uid)},
                {"role":"user","content":text}
            ],
            max_tokens=120
        )
        return r.choices[0].message.content
    except:
        return "Сформулируй нормально"

# ================= AI HR =================
async def ai_review(name, fields):
    text = "\n".join([f"{f['name']}: {f['value']}" for f in fields])

    prompt = """
Ответь JSON:
{"decision":"ok|no|review","reason":"...","score":0-3}
"""

    try:
        r = client.chat.completions.create(
            model=MODEL,
            messages=[{"role":"system","content":prompt},
                      {"role":"user","content":text}]
        )
        data = json.loads(r.choices[0].message.content)
        return data.get("decision","review"), data.get("reason","-"), data.get("score",1)
    except:
        return "review","ошибка",1

def hr_message(decision, name=None, reason="", score=1):
    n = f"{name}," if name else ""

    if score >= 2 and decision == "ok":
        return f"""{n}
✨ Отличные новости!

Мы внимательно рассмотрели твою заявку и готовы принять тебя.

Сильный уровень 💼  
Добро пожаловать 🤍
"""

    if decision == "ok":
        return f"""{n}
✨ Твоя заявка одобрена 🎉
Добро пожаловать 🤍
"""

    if decision == "no":
        return f"""{n}
Спасибо за заявку 💙

К сожалению, сейчас отказ.

📌 Причина:
{reason}

Попробуй позже 🙏
"""

    return f"""{n}
Заявка принята 👀
Скоро ответим 💬
"""

# ================= EMBED =================
def build_embed(app, user):
    emb = discord.Embed(
        title=f"📋 {app['name']}",
        description=f"Статус: {app['status']}",
        timestamp=datetime.utcnow()
    )

    if app["status"]=="Одобрено": emb.color=0x2ecc71
    elif app["status"]=="Отклонено": emb.color=0xe74c3c
    elif app["status"]=="В работе": emb.color=0xf1c40f

    emb.set_thumbnail(url=user.display_avatar.url)

    for f in json.loads(app["fields"]):
        emb.add_field(name=f["name"], value=f["value"], inline=False)

    if app["taken_by"]:
        emb.add_field(name="Взял", value=app["taken_by"], inline=False)

    return emb

def extract_name(app):
    try:
        for f in json.loads(app["fields"]):
            if "имя" in f["name"].lower():
                return f["value"]
    except:
        pass
    return None

# ================= DB ACCESS =================
def get_app(tid):
    cur.execute("SELECT * FROM apps WHERE thread_id=?", (tid,))
    r = cur.fetchone()
    if not r: return None
    keys=["thread_id","user_id","message_id","name","fields","status","taken_by","created_at","last_update"]
    return dict(zip(keys,r))

# ================= ACTION =================
async def handle_action(tid, action, actor):
    app = get_app(tid)
    if not app: return

    if action=="take":
        status="В работе"
        taken=actor
    elif action=="ok":
        status="Одобрено"
        taken=app["taken_by"]
    elif action=="no":
        status="Отклонено"
        taken=app["taken_by"]
    else:
        return

    update_mod(actor, action)

    cur.execute("""
    UPDATE apps SET status=?, taken_by=?, last_update=?
    WHERE thread_id=?
    """,(status,taken,datetime.utcnow().isoformat(),tid))
    conn.commit()

    app = get_app(tid)

    thread = bot.get_channel(tid) or await bot.fetch_channel(tid)
    msg = await thread.fetch_message(app["message_id"])
    user = await bot.fetch_user(app["user_id"])

    await msg.edit(embed=build_embed(app, user))

# ================= BUTTONS =================
class AppView(discord.ui.View):
    def __init__(self,tid):
        super().__init__(timeout=None)
        self.tid=tid

    @discord.ui.button(label="👮 Взять",style=discord.ButtonStyle.primary)
    async def take(self,i,b):
        await handle_action(self.tid,"take",i.user.mention)
        await i.response.send_message("Взято",ephemeral=True)

    @discord.ui.button(label="✅ Одобрить",style=discord.ButtonStyle.success)
    async def ok(self,i,b):
        await handle_action(self.tid,"ok",i.user.mention)
        await i.response.send_message("Ок",ephemeral=True)

    @discord.ui.button(label="❌ Отклонить",style=discord.ButtonStyle.danger)
    async def no(self,i,b):
        await handle_action(self.tid,"no",i.user.mention)
        await i.response.send_message("Отклонено",ephemeral=True)

# ================= CREATE =================
async def create_app(uid,name,fields):
    forum = bot.get_channel(FORUM_CHANNEL_ID)
    data = await forum.create_thread(name=name, content="Новая заявка")
    thread = data.thread

    msg = await thread.send("⏳")

    now = datetime.utcnow().isoformat()

    cur.execute("INSERT INTO apps VALUES(?,?,?,?,?,?,?,?,?)",
        (thread.id,uid,msg.id,name,json.dumps(fields),"Ожидает",None,now,now))
    conn.commit()

    user = await bot.fetch_user(uid)
    await msg.edit(embed=build_embed(get_app(thread.id),user))
    await thread.send(view=AppView(thread.id))

    # AI -> ЛС
    decision,reason,score = await ai_review(name,fields)

    try:
        nm = extract_name(get_app(thread.id))
        await user.send(hr_message(decision,nm,reason,score))
    except:
        pass

# ================= OVERDUE =================
@tasks.loop(minutes=2)
async def check_overdue():
    cur.execute("SELECT thread_id, created_at, status FROM apps")
    rows = cur.fetchall()

    for tid, created, status in rows:
        if status != "Ожидает":
            continue

        created_dt = datetime.fromisoformat(created)
        diff = (datetime.utcnow() - created_dt).total_seconds() / 60

        if diff > OVERDUE_MIN:
            thread = bot.get_channel(tid) or await bot.fetch_channel(tid)
            await thread.send(random.choice([
                "🚨 Заявка горит",
                "🚨 Вы где вообще?",
                "🚨 Работать будем?"
            ]))

        elif diff > REMIND_MIN:
            thread = bot.get_channel(tid) or await bot.fetch_channel(tid)
            await thread.send("⏳ Напоминание: заявка ждёт")

# ================= BOT =================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print("READY")
    check_overdue.start()

@bot.event
async def on_message(message):
    if message.author.bot: return

    if message.channel.id in CHAT_CHANNELS:
        uid = message.author.id

        if is_boss(uid):
            reply = await lena_reply(uid,message.content)
        else:
            if len(message.content) < 4:
                reply = "Нормально напиши"
                update_reputation(uid,-1)
            else:
                reply = await lena_reply(uid,message.content)
                update_reputation(uid,1)

        await message.reply(reply)

    await bot.process_commands(message)

# ================= COMMAND =================
@bot.tree.command(name="рейтинг")
async def rating(i:discord.Interaction):
    cur.execute("SELECT user_id,score FROM reputation ORDER BY score DESC LIMIT 10")
    rows = cur.fetchall()
    text="\n".join([f"<@{u}> — {s}" for u,s in rows])
    await i.response.send_message(text or "Пусто")

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
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",8080)))

threading.Thread(target=run).start()

bot.run(DISCORD_TOKEN)
