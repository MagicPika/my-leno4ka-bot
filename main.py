import discord
from discord.ext import commands
import os, random, asyncio, threading
from flask import Flask, request, jsonify, render_template_string

# ================= НАСТРОЙКИ =================
TOKEN = os.getenv("DISCORD_TOKEN")

FORUM_CHANNEL_ID = 1458885875692732438
SECRET = "2122428Matros"

ADMIN_TOKEN = "admin123"  # пароль для веб-панели (поменяй)

ARMY_SITE = "https://your-site.ru"
ARMY_DISCORD = "https://discord.gg/yourinvite"

COLOR_WAIT = 0x85144b
COLOR_OK = 0x2ecc71
COLOR_NO = 0xe74c3c
COLOR_CALL = 0xf1c40f
COLOR_TIMEOUT = 0x95a5a6

REMIND_AFTER = 12 * 3600
TIMEOUT_AFTER = 24 * 3600

applications = {}

# ================= FLASK =================
app = Flask(__name__)

# ---------- CRM HTML ----------
HTML = """
<html>
<head>
<title>Леночка CRM</title>
<style>
body { font-family: Arial; background:#111; color:white; }
.card {
  background:#1e1e1e; padding:15px; margin:10px;
  border-radius:10px;
}
button {
  margin:5px; padding:5px 10px;
}
</style>
</head>
<body>

<h1>📊 Панель заявок</h1>

{% for id, a in apps.items() %}
<div class="card">
<b>ID:</b> {{id}}<br>
<b>Статус:</b> {{a["status"]}}<br>
<b>Взял:</b> {{a["taken_by"]}}<br>

<button onclick="act('{{id}}','take')">Взять</button>
<button onclick="act('{{id}}','ok')">Одобрить</button>
<button onclick="act('{{id}}','no')">Отказать</button>
</div>
{% endfor %}

<script>
function act(id, action){
 fetch("/action",{
   method:"POST",
   headers:{
     "Content-Type":"application/json",
     "Authorization":"Bearer {{token}}"
   },
   body:JSON.stringify({id:id,action:action})
 }).then(()=>location.reload())
}
</script>

</body>
</html>
"""

# ---------- API ----------
@app.route("/")
def panel():
    token = request.args.get("token")
    if token != ADMIN_TOKEN:
        return "Нет доступа"
    return render_template_string(HTML, apps=applications, token=ADMIN_TOKEN)

@app.route("/action", methods=["POST"])
def action():
    if request.headers.get("Authorization") != f"Bearer {ADMIN_TOKEN}":
        return "no", 403

    data = request.json
    tid = int(data["id"])
    act = data["action"]

    bot.loop.create_task(web_action(tid, act))
    return "ok"

# ---------- ЗАЯВКА ----------
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

# ================= КНОПКИ =================
class AppView(discord.ui.View):
    def __init__(self, thread_id):
        super().__init__(timeout=None)
        self.thread_id = thread_id

    @discord.ui.button(label="👮 Взять", style=discord.ButtonStyle.primary)
    async def take(self, interaction, button):
        applications[self.thread_id]["taken_by"] = str(interaction.user)
        applications[self.thread_id]["status"] = "В работе"
        await interaction.response.send_message("Взято", ephemeral=True)

    @discord.ui.button(label="✅ Одобрить", style=discord.ButtonStyle.success)
    async def ok(self, interaction, button):
        await web_action(self.thread_id, "ok")
        await interaction.response.send_message("Готово", ephemeral=True)

    @discord.ui.button(label="❌ Отказать", style=discord.ButtonStyle.danger)
    async def no(self, interaction, button):
        await web_action(self.thread_id, "no")
        await interaction.response.send_message("Готово", ephemeral=True)

# ================= ЛОГИКА =================
async def process_app(uid, name, fields):
    user = await bot.fetch_user(uid)

    embed = discord.Embed(
        title=f"📋 {name}",
        description="Ожидает",
        color=COLOR_WAIT
    )

    forum = bot.get_channel(FORUM_CHANNEL_ID)
    data = await forum.create_thread(name=name, embed=embed)

    thread = data.thread
    msg = data.message

    applications[thread.id] = {
        "user": uid,
        "thread": thread.id,
        "message": msg.id,
        "status": "Ожидает",
        "taken_by": None
    }

    await thread.send(view=AppView(thread.id))

async def web_action(thread_id, action):
    app_data = applications.get(thread_id)
    if not app_data:
        return

    guild = bot.guilds[0]
    thread = guild.get_thread(thread_id)
    msg = await thread.fetch_message(app_data["message"])

    embed = msg.embeds[0]

    if action == "ok":
        embed.color = COLOR_OK
        embed.description = "✅ Одобрено"
        app_data["status"] = "Одобрено"

    elif action == "no":
        embed.color = COLOR_NO
        embed.description = "❌ Отказ"
        app_data["status"] = "Отказ"

    await msg.edit(embed=embed)

# ================= ЗАПУСК =================
def run():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=run).start()

bot.run(TOKEN)
