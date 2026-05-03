import discord
from discord.ext import commands
import os, asyncio, sqlite3, threading
from flask import Flask, request, jsonify, session, redirect, render_template_string

# ================= CONFIG =================
TOKEN = os.getenv("DISCORD_TOKEN")

FORUM_CHANNEL_ID = 1458885875692732438
SECRET = "2122428Matros"

WEB_LOGIN = "admin"
WEB_PASS = "admin123"

COLOR_WAIT = 0x85144b
COLOR_OK = 0x2ecc71
COLOR_NO = 0xe74c3c
COLOR_TIMEOUT = 0x95a5a6

# ================= DB =================
conn = sqlite3.connect("db.sqlite3", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS apps(
thread_id INTEGER PRIMARY KEY,
user_id INTEGER,
message_id INTEGER,
status TEXT,
taken_by TEXT,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# ================= FLASK =================
app = Flask(__name__)
app.secret_key = "secret_key"

LOGIN_HTML = """
<h2>Login</h2>
<form method="post">
<input name="login" placeholder="login"><br>
<input name="pass" type="password"><br>
<button>Войти</button>
</form>
"""

PANEL_HTML = """
<h1>CRM Панель</h1>

<a href="/logout">Выйти</a>

<table border="1">
<tr>
<th>ID</th><th>Статус</th><th>Взял</th><th>Действия</th>
</tr>

{% for a in apps %}
<tr>
<td>{{a[0]}}</td>
<td>{{a[3]}}</td>
<td>{{a[4]}}</td>
<td>
<button onclick="act('{{a[0]}}','take')">Взять</button>
<button onclick="act('{{a[0]}}','ok')">OK</button>
<button onclick="act('{{a[0]}}','no')">NO</button>
</td>
</tr>
{% endfor %}

</table>

<script>
function act(id,action){
 fetch("/action",{
  method:"POST",
  headers:{"Content-Type":"application/json"},
  body:JSON.stringify({id:id,action:action})
 }).then(()=>location.reload())
}
</script>
"""

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form["login"] == WEB_LOGIN and request.form["pass"] == WEB_PASS:
            session["auth"] = True
            return redirect("/")
    return LOGIN_HTML

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/")
def panel():
    if not session.get("auth"):
        return redirect("/login")

    cur.execute("SELECT * FROM apps ORDER BY created_at DESC")
    apps = cur.fetchall()
    return render_template_string(PANEL_HTML, apps=apps)

@app.route("/action", methods=["POST"])
def action():
    if not session.get("auth"):
        return "no",403

    data = request.json
    bot.loop.create_task(web_action(int(data["id"]), data["action"]))
    return "ok"

@app.route("/zayavka", methods=["POST"])
def zayavka():
    if request.headers.get("Authorization") != f"Bearer {SECRET}":
        return jsonify({"error":"bad"}),401

    data = request.json
    bot.loop.create_task(process_app(
        int(data["discordId"]),
        data.get("authorName","Без имени"),
        data.get("fields",[])
    ))
    return jsonify({"ok":True})

# ================= BOT =================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= VIEW =================
class AppView(discord.ui.View):
    def __init__(self, thread_id):
        super().__init__(timeout=None)
        self.thread_id = thread_id

    @discord.ui.button(label="👮 Взять", style=discord.ButtonStyle.primary)
    async def take(self, interaction, button):
        cur.execute("UPDATE apps SET taken_by=?, status=? WHERE thread_id=?",
                    (str(interaction.user), "В работе", self.thread_id))
        conn.commit()
        await interaction.response.send_message("Взято", ephemeral=True)

    @discord.ui.button(label="✅ Одобрить", style=discord.ButtonStyle.success)
    async def ok(self, interaction, button):
        await web_action(self.thread_id, "ok")
        await interaction.response.send_message("OK", ephemeral=True)

    @discord.ui.button(label="❌ Отказать", style=discord.ButtonStyle.danger)
    async def no(self, interaction, button):
        await web_action(self.thread_id, "no")
        await interaction.response.send_message("NO", ephemeral=True)

# ================= CREATE =================
async def process_app(uid, name, fields):
    user = await bot.fetch_user(uid)

    embed = discord.Embed(
        title=f"📋 {name}",
        description="Ожидает",
        color=COLOR_WAIT
    )

    embed.add_field(name="Пользователь", value=f"<@{uid}>")

    forum = bot.get_channel(FORUM_CHANNEL_ID)
    data = await forum.create_thread(name=name, embed=embed)

    thread = data.thread
    msg = data.message

    cur.execute("INSERT INTO apps VALUES(?,?,?,?,?,CURRENT_TIMESTAMP)",
                (thread.id, uid, msg.id, "Ожидает", None))
    conn.commit()

    await thread.send(view=AppView(thread.id))

# ================= ACTION =================
async def web_action(thread_id, action):
    cur.execute("SELECT message_id FROM apps WHERE thread_id=?", (thread_id,))
    row = cur.fetchone()
    if not row:
        return

    message_id = row[0]

    guild = bot.guilds[0]
    thread = guild.get_thread(thread_id)
    msg = await thread.fetch_message(message_id)

    embed = msg.embeds[0]

    if action == "ok":
        embed.color = COLOR_OK
        embed.description = "✅ Одобрено"
        cur.execute("UPDATE apps SET status=? WHERE thread_id=?", ("Одобрено", thread_id))

    elif action == "no":
        embed.color = COLOR_NO
        embed.description = "❌ Отклонено"
        cur.execute("UPDATE apps SET status=? WHERE thread_id=?", ("Отклонено", thread_id))

    conn.commit()
    await msg.edit(embed=embed)

# ================= COMMAND =================
@bot.command()
async def панель(ctx):
    await ctx.send("CRM: /login")

# ================= RUN =================
def run():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=run).start()

bot.run(TOKEN)
