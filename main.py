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
    print(f"Обрабатываю заявку от {discord_id} ({author_name})")
    sys.stdout.flush()

    try:
        user = await bot.fetch_user(discord_id)
        avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
    except Exception as e:
        print(f"Не удалось взять аватарку {discord_id}: {e}")
        avatar_url = f"https://cdn.discordapp.com/embed/avatars/{discord_id % 6}.png"
    sys.stdout.flush()

    embed = discord.Embed(
        title=f"Заявка от {author_name}",
        description="Ожидает решения боссов",
        color=0xED1FFC,
        timestamp=discord.utils.utcnow()
    )
    embed.set_thumbnail(url=avatar_url)

    # Добавляем поля заявки
    embed.add_field(name="Discord ID", value=f"<@{discord_id}>", inline=False)
    for f in fields:
        embed.add_field(name=f["name"], value=f["value"] or "—", inline=f.get("inline", False))
    embed.set_footer(
        text="Поставьте ✅ для одобрения, ❌ для отклонения, 📞 для уточнения.",
        icon_url="https://media.discordapp.net/attachments/1342349362600218624/1459185809654808608/ChatGPT_Image_4_._2026_._15_58_32.png"
    )

    # Получаем форумный канал
    channel = bot.get_channel(FORUM_CHANNEL_ID)
    if not channel:
        print("Форумный канал не найден")
        return

    # Создаем тред
    thread_with_msg = await channel.create_thread(
        name=f"Заявка — {author_name}",
        embed=embed,
        auto_archive_duration=10080
    )

    # Для отправки сообщений берем канал по ID
    thread = bot.get_channel(thread_with_msg.id)

    # Кнопки для админов
    class КнопкиЗаявки(discord.ui.View):
        def __init__(self, user: discord.User):
            super().__init__(timeout=None)
            self.user = user

        @discord.ui.button(label="✅ Одобрить", style=discord.ButtonStyle.success)
        async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
            guild = interaction.guild
            member = guild.get_member(self.user.id)
            if member:
                # Убираем роль "На проверке"
                role_check = guild.get_role(РОЛЬ_НА_ПРОВЕРКЕ)
                if role_check in member.roles:
                    await member.remove_roles(role_check)
                # Добавляем роль "Одобрено"
                role_ok = guild.get_role(РОЛЬ_ОДОБРЕНО)
                if role_ok:
                    await member.add_roles(role_ok)
            await self.user.send(random.choice(РОФЛ_ОДОБРЕНО))
            await interaction.response.send_message(f"Заявка {self.user.mention} одобрена ✅", ephemeral=True)
            self.stop()

        @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.danger)
        async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.user.send(random.choice(РОФЛ_ОТКЛОНЕНО))
            await interaction.response.send_message(f"Заявка {self.user.mention} отклонена ❌", ephemeral=True)
            self.stop()

        @discord.ui.button(label="📞 Уточнить", style=discord.ButtonStyle.secondary)
        async def clarify(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.user.send(random.choice(РОФЛ_УТОЧНИТЬ))
            await interaction.response.send_message(f"Попросили уточнения у {self.user.mention} 📞", ephemeral=True)
            self.stop()

    view = КнопкиЗаявки(user)

    # Пингуем боссов
    ping = f"<@924956705756971028> <@695943956856307744> <@&1457319043672576008>"
    await thread.send(ping + " новая заявка! Леночка ждёт решения~ 💌", view=view)

    # Роль "На проверке"
    try:
        guild = bot.get_guild(thread.guild.id)
        member = guild.get_member(discord_id)
        role_check = guild.get_role(РОЛЬ_НА_ПРОВЕРКЕ)
        if member and role_check:
            await member.add_roles(role_check, reason="Новая заявка — на проверке")
    except Exception as e:
        print(f"Ошибка выдачи роли 'На проверке': {e}")

    # ЛС заявителю
    try:
        await user.send(random.choice(РОФЛ_ПОЛУЧЕНО))
    except Exception as e:
        print(f"Не получилось написать в ЛС {discord_id}: {e}")

    # Таймеры Леночки
    async def таймер_леночки():
        await asyncio.sleep(24 * 3600)  # 24 часа
        try:
            await thread.send("Боссики, прошло 24 часа, Леночка напоминает о заявке 😌")
        except:
            pass

    bot.loop.create_task(таймер_леночки())

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


