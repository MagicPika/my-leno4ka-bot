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
    "openrouter/auto",
    "mistralai/mistral-7b-instruct:free"
]

GPT_ENABLED = True
CACHE = {}

# ================= DIALOG =================
DIALOGS = {}
DIALOG_TIMEOUT = 60

def start_dialog(uid): DIALOGS[uid] = time.time()

def in_dialog(uid):
    if uid not in DIALOGS: return False
    if time.time() - DIALOGS[uid] > DIALOG_TIMEOUT:
        del DIALOGS[uid]
        return False
    return True

def refresh_dialog(uid): DIALOGS[uid] = time.time()

# ================= TRIGGERS =================
TRIGGERS = ["леночка","лена","лен"]
COMMAND_WORDS = ["помоги","что делать","как вступить","объясни"]

def is_lena_call(text):
    t = text.lower()
    return any(x in t for x in TRIGGERS) or any(x in t for x in COMMAND_WORDS)

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
logs TEXT,
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
Ты Леночка. Живой человек.
Отвечай только на русском.
Коротко (1-2 предложения).
С характером.
Поддерживай диалог.
"""

# ================= GPT =================
def fallback(text):
    return random.choice(["Ты серьёзно?","Сам подумай","Заявку открой"])

async def lena_reply(uid, text):
    key = text.lower()
    if key in CACHE:
        return CACHE[key]

    messages = [
        {"role":"system","content":persona()},
        *load_memory(uid),
        {"role":"user","content":text}
    ]

    for m in MODELS:
        try:
            r = client.chat.completions.create(
                model=m,
                messages=messages,
                max_tokens=120
            )
            ans = r.choices[0].message.content
            if ans:
                save_message(uid,"user",text)
                save_message(uid,"assistant",ans)
                CACHE[key]=ans
                return ans
        except Exception as e:
            print("GPT FAIL:",e)

    return fallback(text)

# ================= AI REVIEW =================
async def ai_review_application(name, fields):
    try:
        text = "\n".join([f"{f['name']}: {f['value']}" for f in fields])

        messages = [
            {"role":"system","content":
            """Ты проверяешь заявки.
Ответ JSON:
{"decision":"ok|no|review","reason":"..."}"""},

            {"role":"user","content":text}
        ]

        r = client.chat.completions.create(
            model="openrouter/auto",
            messages=messages,
            max_tokens=120
        )

        data = json.loads(r.choices[0].message.content)
        d = data.get("decision","review")
        if d not in ["ok","no","review"]:
            d="review"
        return d, data.get("reason","-")

    except Exception as e:
        print("AI ERROR",e)
        return "review","ошибка"

# ================= EMBED =================
def build_embed(app, user):
    emb = discord.Embed(
        title=f"📋 {app['name']}",
        description=f"Статус: {app['status']}",
        color=COLOR_WAIT,
        timestamp=datetime.utcnow()
    )
    emb.set_thumbnail(url=user.display_avatar.url)

    for f in json.loads(app["fields"]):
        emb.add_field(name=f["name"], value=f["value"], inline=False)

    if app["taken_by"]:
        emb.add_field(name="Взял", value=app["taken_by"], inline=False)

    return emb

# ================= STATS =================
def update_mod_stats(user, action):
    cur.execute("""
    INSERT INTO mod_stats(user,taken,approved,rejected)
    VALUES(?,?,?,?)
    ON CONFLICT(user) DO UPDATE SET
    taken=taken+?,
    approved=approved+?,
    rejected=rejected+?
    """,(
        user,
        1 if action=="take" else 0,
        1 if action=="ok" else 0,
        1 if action=="no" else 0,
        1 if action=="take" else 0,
        1 if action=="ok" else 0,
        1 if action=="no" else 0
    ))
    conn.commit()

# ================= APP =================
def get_app(tid):
    cur.execute("SELECT * FROM apps WHERE thread_id=?",(tid,))
    row = cur.fetchone()
    if not row: return None
    keys=["thread_id","user_id","message_id","name","fields","status","taken_by","logs","created_at"]
    return dict(zip(keys,row))

async def handle_action(tid, action, actor):
    app = get_app(tid)
    if not app: return

    user = await bot.fetch_user(app["user_id"])

    if action=="take":
        app["status"]="В работе"
        app["taken_by"]=actor
    elif action=="ok":
        app["status"]="Одобрено"
    elif action=="no":
        app["status"]="Отклонено"

    update_mod_stats(actor, action)

    cur.execute("UPDATE apps SET status=?,taken_by=? WHERE thread_id=?",
                (app["status"],app.get("taken_by"),tid))
    conn.commit()

    thread = bot.get_channel(tid)
    if not thread: return

    msg = await thread.fetch_message(app["message_id"])
    emb = build_embed(get_app(tid), user)

    if app["status"]=="Одобрено": emb.color=COLOR_OK
    elif app["status"]=="Отклонено": emb.color=COLOR_NO
    elif app["status"]=="В работе": emb.color=COLOR_WORK

    await msg.edit(embed=emb)

    try:
        await user.send(f"Ваша заявка: {app['status']}")
    except: pass

# ================= BUTTONS =================
class AppView(discord.ui.View):
    def __init__(self,tid):
        super().__init__(timeout=None)
        self.tid=tid

    @discord.ui.button(label="👮 Взять",style=discord.ButtonStyle.primary)
    async def take(self,i,b):
        await handle_action(self.tid,"take",i.user.mention)
        await i.response.send_message("OK",ephemeral=True)

    @discord.ui.button(label="✅ Одобрить",style=discord.ButtonStyle.success)
    async def ok(self,i,b):
        await handle_action(self.tid,"ok",i.user.mention)
        await i.response.send_message("OK",ephemeral=True)

    @discord.ui.button(label="❌ Отклонить",style=discord.ButtonStyle.danger)
    async def no(self,i,b):
        await handle_action(self.tid,"no",i.user.mention)
        await i.response.send_message("OK",ephemeral=True)

# ================= CREATE =================
async def create_app(uid,name,fields):
    forum = bot.get_channel(FORUM_CHANNEL_ID)
    data = await forum.create_thread(name=name,content="Новая заявка")
    thread = data.thread

    msg = await thread.send("⏳")

    cur.execute("INSERT INTO apps VALUES(?,?,?,?,?,?,?,?,?)",
        (thread.id,uid,msg.id,name,json.dumps(fields),
         "Ожидает",None,json.dumps([]),
         datetime.utcnow().isoformat()))
    conn.commit()

    user = await bot.fetch_user(uid)
    await msg.edit(embed=build_embed(get_app(thread.id),user))
    await thread.send(view=AppView(thread.id))

    # ===== AI REVIEW =====
    decision, reason = await ai_review_application(name,fields)
    await thread.send(f"🤖 AI: {decision}\n{reason}")

    if decision=="ok":
        await handle_action(thread.id,"ok","AI")
    elif decision=="no":
        await handle_action(thread.id,"no","AI")

# ================= OVERDUE =================
async def check_overdue():
    await bot.wait_until_ready()
    while True:
        cur.execute("SELECT thread_id,created_at,status FROM apps")
        for tid,created,status in cur.fetchall():
            if status in ["Одобрено","Отклонено"]: continue

            minutes=(datetime.utcnow()-datetime.fromisoformat(created)).total_seconds()/60
            thread=bot.get_channel(tid)
            if not thread: continue

            if minutes>REMIND_MINUTES:
                await thread.send(f"<@&{MOD_ROLE_ID}> возьмите заявку")

            if minutes>OVERDUE_MINUTES:
                await thread.send("🚨 Леночка: вы там живые?")

        await asyncio.sleep(60)

# ================= WEB =================
app = Flask(__name__)

@app.route("/")
def dash():
    cur.execute("SELECT thread_id,name,status,taken_by FROM apps")
    rows=cur.fetchall()
    html="<h1>CRM</h1>"
    for r in rows:
        html+=f"{r[1]} | {r[2]} | {r[3]} <a href='/ok/{r[0]}'>OK</a><br>"
    return html

@app.route("/ok/<int:tid>")
def ok_web(tid):
    bot.loop.create_task(handle_action(tid,"ok","WEB"))
    return "ok"

# ================= BOT =================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_message(message):
    if message.author.bot: return

    if GPT_ENABLED and message.channel.id in CHAT_CHANNELS:
        uid=message.author.id
        called = bot.user in message.mentions or is_lena_call(message.content)
        active = in_dialog(uid)

        if called: start_dialog(uid)

        if called or active:
            refresh_dialog(uid)
            reply = await lena_reply(uid,message.content)
            await message.reply(reply)

    await bot.process_commands(message)

@bot.tree.command(name="гпт")
async def gpt_cmd(i:discord.Interaction,mode:str):
    global GPT_ENABLED
    GPT_ENABLED = (mode=="on")
    await i.response.send_message("OK",ephemeral=True)

@bot.tree.command(name="стата")
async def stats(i:discord.Interaction):
    cur.execute("SELECT * FROM mod_stats")
    rows=cur.fetchall()
    text="\n".join([str(r) for r in rows])
    await i.response.send_message(text or "Пусто")

@bot.event
async def on_ready():
    await bot.tree.sync()
    bot.loop.create_task(check_overdue())
    print("READY")

def run():
    app.run(host="0.0.0.0",port=int(os.getenv("PORT",8080)))

threading.Thread(target=run).start()

bot.run(DISCORD_TOKEN)
