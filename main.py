import discord
from discord.ext import commands
import os, asyncio, sqlite3, json, threading
from datetime import datetime
from flask import Flask, request, jsonify, session, redirect, render_template_string

TOKEN = os.getenv("DISCORD_TOKEN")
FORUM_CHANNEL_ID = 1458885875692732438
SECRET = "2122428Matros"

WEB_LOGIN = "admin"
WEB_PASS = "admin123"

COLOR_WAIT = 0x85144b
COLOR_OK = 0x2ecc71
COLOR_NO = 0xe74c3c
COLOR_WORK = 0xf1c40f

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
CREATE TABLE IF NOT EXISTS stats(
user TEXT PRIMARY KEY,
accepted INTEGER,
rejected INTEGER
)
""")
conn.commit()

# ================= FLASK =================
app = Flask(__name__)
app.secret_key = "secret"

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form["login"] == WEB_LOGIN and request.form["pass"] == WEB_PASS:
            session["auth"] = True
            return redirect("/")
    return "<form method=post><input name=login><input name=pass type=password><button>Login</button>"

@app.route("/")
def panel():
    if not session.get("auth"):
        return redirect("/login")

    cur.execute("SELECT thread_id,status,taken_by FROM apps ORDER BY created_at DESC")
    rows = cur.fetchall()

    html = "<h1>CRM</h1>"
    for r in rows:
        html += f"""
        <div>
        #{r[0]} | {r[1]} | {r[2]}
        <button onclick="act({r[0]},'take')">Взять</button>
        <button onclick="act({r[0]},'ok')">OK</button>
        <button onclick="act({r[0]},'no')">NO</button>
        </div>
        """

    html += """
    <script>
    function act(id,a){
    fetch("/action",{method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({id:id,action:a})}).then(()=>location.reload())
    }
    </script>
    """

    return html

@app.route("/action", methods=["POST"])
def action():
    if not session.get("auth"):
        return "no",403
    data = request.json
    bot.loop.create_task(handle_action(data["id"], data["action"], "WEB"))
    return "ok"

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

# ================= BOT =================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= EMBED =================
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
        log_text = "\n".join(logs[-5:])
        embed.add_field(name="📜 История", value=log_text, inline=False)

    embed.set_footer(text="Леночка PRO 💌")
    return embed

# ================= CREATE =================
async def create_app(uid, name, fields):
    user = await bot.fetch_user(uid)

    logs = [f"🟡 Создана: {datetime.utcnow().strftime('%H:%M')}"]

    cur.execute("INSERT INTO apps VALUES(?,?,?,?,?,?,?,?,?)",
        (0, uid, 0, name, json.dumps(fields), "Ожидает", None, json.dumps(logs), datetime.utcnow().isoformat()))
    conn.commit()

    forum = bot.get_channel(FORUM_CHANNEL_ID)
    temp = await forum.create_thread(name=name, content="Создание...")

    thread = temp.thread
    msg = await thread.send("...")

    cur.execute("UPDATE apps SET thread_id=?, message_id=? WHERE thread_id=0",
                (thread.id, msg.id))
    conn.commit()

    app_data = get_app(thread.id)
    embed = build_embed(app_data, user)

    await msg.edit(embed=embed, content=None)
    await thread.send(view=AppView(thread.id))

# ================= ACTION =================
def get_app(tid):
    cur.execute("SELECT * FROM apps WHERE thread_id=?", (tid,))
    row = cur.fetchone()
    keys = ["thread_id","user_id","message_id","name","fields","status","taken_by","logs","created_at"]
    return dict(zip(keys,row))

async def handle_action(tid, action, actor):
    app_data = get_app(tid)
    user = await bot.fetch_user(app_data["user_id"])

    logs = json.loads(app_data["logs"])

    if action == "take":
        app_data["taken_by"] = actor
        app_data["status"] = "В работе"
        logs.append(f"👮 Взял: {actor}")

    elif action == "ok":
        app_data["status"] = "Одобрено"
        logs.append(f"✅ Одобрил: {actor}")

    elif action == "no":
        app_data["status"] = "Отклонено"
        logs.append(f"❌ Отклонил: {actor}")

    cur.execute("""
    UPDATE apps SET status=?, taken_by=?, logs=?
    WHERE thread_id=?
    """, (app_data["status"], app_data["taken_by"], json.dumps(logs), tid))
    conn.commit()

    guild = bot.guilds[0]
    thread = guild.get_thread(tid)
    msg = await thread.fetch_message(app_data["message_id"])

    embed = build_embed(get_app(tid), user)

    if app_data["status"] == "Одобрено":
        embed.color = COLOR_OK
    elif app_data["status"] == "Отклонено":
        embed.color = COLOR_NO
    elif app_data["status"] == "В работе":
        embed.color = COLOR_WORK

    await msg.edit(embed=embed)

    if app_data["status"] in ["Одобрено","Отклонено"]:
        await asyncio.sleep(5)
        await thread.edit(archived=True, locked=True)

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

    @discord.ui.button(label="❌ Отказать", style=discord.ButtonStyle.danger)
    async def no(self, i, b):
        await handle_action(self.tid, "no", i.user.mention)
        await i.response.send_message("Ок", ephemeral=True)

# ================= RUN =================
def run():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=run).start()

bot.run(TOKEN)
