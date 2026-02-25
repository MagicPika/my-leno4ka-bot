# main.py
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View
from discord.ui import Button
from flask import Flask, request, jsonify
import threading, random, asyncio, os, sys, datetime

# === НАСТРОЙКИ ===
TOKEN = os.getenv("DISCORD_TOKEN")
FORUM_CHANNEL_ID = 1458881043653197896
LOG_CHANNEL_ID = 1286768393478733887  # канал для логов (добавь свой ID)
SECRET = "2122428Matros"

РОЛЬ_НА_ПРОВЕРКЕ = 1473913094697783380
РОЛЬ_ОДОБРЕНО = 1473913198016069642

# ── Смешные сообщения для заявок ───────────────────────────────
РОФЛ_ПОЛУЧЕНО = [
    "Ооо, свеженькая заявОчка прилетела~ Леночка уже несёт боссам...",
    "Привеет, красавчик… Леночка увидела твою анкету...",
]
РОФЛ_ОДОБРЕНО = [
    "Урааа~ 💕 Боссы сказали ДА! Заходи скорее...",
    "Одобрено! Леночка в полном восторге, ты прошёл!",
]
РОФЛ_ОТКЛОНЕНО = [
    "Ой-ой… боссы сказали нет 😔 Но не грусти...",
    "К сожалению, отказ… Леночка расстроилась вместе с тобой…",
]
РОФЛ_УТОЧНИТЬ = [
    "Боссы хотят уточнить детали! Напиши в канал или ЛС Леночке...",
    "📞 Звоночек! Нужно кое-что уточнить, ждём тебя~",
]

# ── Flask ───────────────────────────────
app = Flask(__name__)

@app.route("/zayavka", methods=["POST"])
def принимать_заявку():
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {SECRET}":
        return jsonify({"error": "Неверный ключ"}), 401

    data = request.json or {}
    discord_id = data.get("discordId")
    author_name = data.get("authorName", "Без имени")
    fields = data.get("fields", [])

    if not discord_id or not str(discord_id).isdigit():
        return jsonify({"error": "Нет нормального discordId"}), 400

    bot.loop.create_task(обработать_заявку_2_0(int(discord_id), author_name, fields))
    return jsonify({"status": "ok"}), 200

# ── Асинхронная обработка заявки с кнопками ───────────────────────────────
async def обработать_заявку_2_0(discord_id: int, author_name: str, fields: list):
    try:
        user = await bot.fetch_user(discord_id)
        avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
    except:
        avatar_url = f"https://cdn.discordapp.com/embed/avatars/{discord_id % 6}.png"

    embed = discord.Embed(
        title=f"Заявка от {author_name}",
        description="Ожидает решения боссов",
        color=0xff69b4,
        timestamp=discord.utils.utcnow()
    )
    embed.set_thumbnail(url=avatar_url)
    embed.add_field(name="Discord ID", value=f"<@{discord_id}>", inline=False)
    for f in fields:
        embed.add_field(name=f["name"], value=f.get("value", "—"), inline=f.get("inline", False))

    channel = bot.get_channel(FORUM_CHANNEL_ID)
    if not channel:
        print("Форумный канал не найден")
        return

    view = View()
    view.add_item(Button(label="✅ Одобрено", style=discord.ButtonStyle.success, custom_id=f"approve_{discord_id}"))
    view.add_item(Button(label="❌ Отклонено", style=discord.ButtonStyle.danger, custom_id=f"reject_{discord_id}"))
    view.add_item(Button(label="📞 Уточнить", style=discord.ButtonStyle.secondary, custom_id=f"clarify_{discord_id}"))

    thread = await channel.create_thread(
        name=f"Заявка — {author_name}",
        embed=embed,
        auto_archive_duration=10080
    )
    await thread.send(f"<@&{РОЛЬ_НА_ПРОВЕРКЕ}> новая заявка! Леночка ждёт решения~ 💌", view=view)

    # Выдаём роль "На проверке"
    guild = thread.guild
    member = await guild.fetch_member(discord_id)
    роль_проверка = guild.get_role(РОЛЬ_НА_ПРОВЕРКЕ)
    if member and роль_проверка:
        await member.add_roles(роль_проверка, reason="Новая заявка — на проверке")

    # ЛС заявителю
    try:
        await user.send(random.choice(РОФЛ_ПОЛУЧЕНО))
    except:
        pass

    # Логируем в лог-канал
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(f"Новая заявка от <@{discord_id}>: {author_name}")

# ── Обработчик кнопок ───────────────────────────────
class ЗаявкаView(View):
    def __init__(self):
        super().__init__(timeout=None)  # без таймаута

    @discord.ui.button(label="✅ Одобрено", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        await handle_verdict(interaction, "approve")

    @discord.ui.button(label="❌ Отклонено", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await handle_verdict(interaction, "reject")

    @discord.ui.button(label="📞 Уточнить", style=discord.ButtonStyle.secondary)
    async def clarify(self, interaction: discord.Interaction, button: discord.ui.Button):
        await handle_verdict(interaction, "clarify")

async def handle_verdict(interaction: discord.Interaction, verdict: str):
    embed = interaction.message.embeds[0] if interaction.message.embeds else None
    if not embed:
        return
    discord_id_field = [f.value for f in embed.fields if f.name == "Discord ID"]
    if not discord_id_field:
        return
    discord_id = int(''.join(c for c in discord_id_field[0] if c.isdigit()))
    guild = interaction.guild
    member = await guild.fetch_member(discord_id)
    if not member:
        return

    роль_проверка = guild.get_role(РОЛЬ_НА_ПРОВЕРКЕ)
    роль_одобрено = guild.get_role(РОЛЬ_ОДОБРЕНО)

    if роль_проверка in member.roles:
        await member.remove_roles(роль_проверка, reason="Заявка обработана")

    if verdict == "approve" and роль_одобрено:
        await member.add_roles(роль_одобрено, reason="Заявка одобрена")
        текст = random.choice(РОФЛ_ОДОБРЕНО)
    elif verdict == "reject":
        текст = random.choice(РОФЛ_ОТКЛОНЕНО)
    else:
        текст = random.choice(РОФЛ_УТОЧНИТЬ)

    try:
        await member.send(текст)
    except:
        pass

    await interaction.response.send_message(f"Решение принято: {verdict} для <@{discord_id}>", ephemeral=True)

    # Лог
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(f"{interaction.user.mention} принял решение {verdict} по заявке <@{discord_id}>")

# ── Запуск Flask и бот ───────────────────────────────
def run_flask():
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)

threading.Thread(target=run_flask, daemon=True).start()

# ── Настройка бота ───────────────────────────────
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Леночка готова → {bot.user}")
    await bot.tree.sync()
    print("Слэш-команды синхронизированы")

# ── Команды и функции Леночки (оставляем старые) ───────────────────────────────
@bot.command(name="статус")
async def статус_заявок(ctx):
    await ctx.send("Здесь будет статус заявок (можно расширить под кнопки и теги)")

@bot.command(name="похвали")
async def похвали(ctx, member: discord.Member = None):
    if member is None:
        участники = [m for m in ctx.guild.members if not m.bot and m.status != discord.Status.offline]
        if not участники:
            await ctx.send("Никого онлайн нет...")
            return
        member = random.choice(участники)
    await ctx.send(f"{member.mention}, Леночка говорит: ты молодец! 💕")

bot.run(TOKEN)

