import discord
from discord.ext import commands
import os, asyncio, sqlite3, json, threading
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
        print(f"[ERROR] Заявка {tid} не найдена")
        return None

    keys = ["thread_id","user_id","message_id","name","fields","status","taken_by","logs","created_at"]
    return dict(zip(keys, row))


async def get_thread_safe(tid):
    # 1. пробуем из кеша
    channel = bot.get_channel(tid)

    # 2. если нет — через API
    if not channel:
        try:
            channel = await bot.fetch_channel(tid)
        except Exception as e:
            print(f"[ERROR] fetch_channel {tid}: {e}")
            return None

    return channel


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
        avatar = user.avatar.url if user.avatar else user.default_avatar.url
        embed.set_thumbnail(url=avatar)
    except:
        pass

    embed.add_field(
        name="👤 Пользователь",
        value=f"<@{app_data['user_id']}> (`{app_data['user_id']}`)",
        inline=False
    )

    for f in fields:
        embed.add_field(name=f["name"], value=f["value"], inline=False)

    if app_data["taken_by"]:
        embed.add_field(name="👮 Взял", value=app_data["taken_by"], inline=False)

    if logs:
        embed.add_field(
            name="📜 История",
            value="\n".join(logs[-5:]),
            inline=False
        )

    embed.set_footer(text="Леночка 💌")
    return embed

# ================= CREATE =================
async def create_app(uid, name, fields):
    try:
        user = await bot.fetch_user(uid)
    except:
        print(f"[ERROR] Не удалось получить пользователя {uid}")
        return

    logs = [f"🟡 Создана {datetime.utcnow().strftime('%H:%M')}"]

    forum = bot.get_channel(FORUM_CHANNEL_ID)
    if not forum:
        print("Форум не найден")
        return

    # создаём тред
    data = await forum.create_thread(name=name, content="Создание заявки...")
    thread = data.thread

    msg = await thread.send("⏳ Загрузка...")

    # сохраняем
    cur.execute("""
    INSERT INTO apps VALUES(?,?,?,?,?,?,?,?,?)
    """, (
        thread.id,
        uid,
        msg.id,
        name,
        json.dumps(fields),
        "Ожидает",
        None,
        json.dumps(logs),
        datetime.utcnow().isoformat()
    ))
    conn.commit()

    app_data = get_app(thread.id)
    embed = build_embed(app_data, user)

    await msg.edit(content=None, embed=embed)
    await thread.send(view=AppView(thread.id))


# ================= ACTION =================
async def handle_action(tid, action, actor):
    app_data = get_app(tid)
    if not app_data:
        return

    try:
        user = await bot.fetch_user(app_data["user_id"])
    except:
        print("user fetch fail")
        return

    logs = json.loads(app_data["logs"])

    # ===== логика статуса =====
    if action == "take":
        app_data["status"] = "В работе"
        app_data["taken_by"] = actor
        logs.append(f"👮 Взял: {actor}")

    elif action == "ok":
        app_data["status"] = "Одобрено"
        logs.append(f"✅ Одобрил: {actor}")

    elif action == "no":
        app_data["status"] = "Отклонено"
        logs.append(f"❌ Отклонил: {actor}")

    cur.execute("""
    UPDATE apps SET status=?, taken_by=?, logs=? WHERE thread_id=?
    """, (
        app_data["status"],
        app_data["taken_by"],
        json.dumps(logs),
        tid
    ))
    conn.commit()

    # ===== ПОЛУЧЕНИЕ ТРЕДА (железобетон) =====
    thread = None

    # 1. кеш
    channel = bot.get_channel(tid)

    # 2. API
    if not channel:
        try:
            channel = await bot.fetch_channel(tid)
        except Exception as e:
            print(f"[ERROR] fetch_channel {tid}: {e}")
            return

    # 3. проверка что это именно тред
    if isinstance(channel, discord.Thread):
        thread = channel
    else:
        print(f"[ERROR] Это не тред: {type(channel)}")
        return

    # ===== ПОЛУЧЕНИЕ СООБЩЕНИЯ =====
    msg = None
    try:
        msg = await thread.fetch_message(app_data["message_id"])
    except:
        try:
            # fallback через историю
            async for m in thread.history(limit=50):
                if m.id == app_data["message_id"]:
                    msg = m
                    break
        except Exception as e:
            print(f"[ERROR] history fail: {e}")
            return

    if not msg:
        print(f"[ERROR] сообщение не найдено {tid}")
        return

    # ===== ОБНОВЛЕНИЕ EMBED =====
    updated = get_app(tid)
    embed = build_embed(updated, user)

    if updated["status"] == "Одобрено":
        embed.color = COLOR_OK
    elif updated["status"] == "Отклонено":
        embed.color = COLOR_NO
    elif updated["status"] == "В работе":
        embed.color = COLOR_WORK

    try:
        await msg.edit(embed=embed)
    except Exception as e:
        print(f"[ERROR] edit fail: {e}")


# ================= BUTTONS =================
class AppView(discord.ui.View):
    def __init__(self, tid):
        super().__init__(timeout=None)
        self.tid = tid

    @discord.ui.button(label="👮 Взять", style=discord.ButtonStyle.primary)
    async def take(self, i, b):
        await handle_action(self.tid, "take", i.user.mention)
        await i.response.send_message("Взято", ephemeral=True)

    @discord.ui.button(label="✅ Одобрить", style=discord.ButtonStyle.success)
    async def ok(self, i, b):
        await handle_action(self.tid, "ok", i.user.mention)
        await i.response.send_message("Одобрено", ephemeral=True)

    @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.danger)
    async def no(self, i, b):
        await handle_action(self.tid, "no", i.user.mention)
        await i.response.send_message("Отклонено", ephemeral=True)


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
