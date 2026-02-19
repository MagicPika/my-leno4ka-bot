# main.py
import discord
from discord.ext import commands
import os
from flask import Flask, request, jsonify
import threading
import random

app = Flask(__name__)

# === НАСТРОЙКИ ===
TOKEN = os.getenv("DISCORD_TOKEN")
FORUM_CHANNEL_ID = 1458881043653197896     # ← реальный ID форумного канала
SECRET = "2122428Matros"   # ← меняй обязательно

РОЛЬ_НА_ПРОВЕРКЕ = 1473913094697783380     # ← ID роли "На проверке"
РОЛЬ_ОДОБРЕНО    = 1473913198016069642     # ← ID роли "Одобрен"

РОФЛ_ПОЛУЧЕНО = [
    "Привеет~ 💕 Леночка увидела твою заявку и уже понесла боссам! Жди вердикта, не скучай ☕",
    "Ой, какая сочная заявОчка! Леночка в восторге, сейчас покажу Кириллу/Ивану 😘",
    "Всё-всё, поняла! Заявка ушла наверх. Держи пальчики скрещенными 💋",
    "Твоя заявка принята, котик! Леночка доложила, теперь только ждать~ ✨"
]

РОФЛ_ОДОБРЕНО = [
    "Урааа~ 💕 Твоя заявка одобрена! Заходи скорее, Леночка уже наливает кофе ☕",
    "Боссы сказали ДА! Добро пожаловать, солнышко 😘",
    "Одобрено! Леночка в восторге, ты прошёл~ ❤️"
]

РОФЛ_ОТКЛОНЕНО = [
    "Ой-ой… боссы сказали нет 😔 Но не грусти, Леночка всё равно тебя любит 💔",
    "К сожалению, отказ… Но в следующий раз Леночка за тебя лучше замолвит словечко 😉",
    "Не прошли… Но ты милый, приходи попить чайку с Леночкой ☕"
]

РОФЛ_УТОЧНИТЬ = [
    "Боссы хотят уточнить детали! Напиши в канал или в ЛС Леночке 📞",
    "📞 Звоночек! Нужно кое-что уточнить, ждём тебя~",
    "Ой, боссам мало инфы… Напиши подробнее, пожалуйста 💕"
]

# Flask — принимает заявки из формы
@app.route("/zayavka", methods=["POST"])
def принимать_заявку():
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {SECRET}":
        print("Неверный ключ авторизации")
        return jsonify({"error": "Неверный ключ"}), 401

    data = request.json or {}
    discord_id = data.get("discordId")
    author_name = data.get("authorName", "Без имени")
    fields = data.get("fields", [])
    mention = data.get("mention", "Не указан")
    ic = data.get("ic", "Не указан")

    print(f"Получена заявка: discordId={discord_id}, имя={author_name}")

    if not discord_id or not str(discord_id).isdigit():
        print("Нет нормального discordId")
        return jsonify({"error": "Нет нормального discordId"}), 400

    bot.loop.create_task(обработать_заявку(int(discord_id), author_name, fields, mention, ic))
    return jsonify({"status": "ok"}), 200


# Основная обработка заявки
async def обработать_заявку(discord_id: int, author_name: str, fields: list, mention: str, ic: str):
    print(f"Обрабатываю заявку от {discord_id} ({author_name})")

    try:
        user = await bot.fetch_user(discord_id)
        avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
        print(f"Аватарка найдена для {discord_id}")
    except Exception as e:
        print(f"Не удалось взять аватарку {discord_id}: {e}")
        avatar_url = f"https://cdn.discordapp.com/embed/avatars/{discord_id % 6}.png"

    босс = random.choice(["Кирилл Иванов", "Иван Иванов"])
    рофл_заголовок = random.choice([
        "Ой-ой, свеженькая заявОчка прилетела~ 💅",
        "Минутку, котик, Леночка уже несёт боссам! 😏",
        "Заявочка от красавчика! Сейчас покажу Кириллу/Ивану ☕",
        "Ух ты, кто-то решил вступить! Леночка в деле ✨"
    ])

    embed = discord.Embed(
        title=рофл_заголовок,
        description=f"{mention} {ic}",
        color=13369344,
        timestamp=discord.utils.utcnow()
    )
    embed.set_author(
        name="Кадровый отдел",
        icon_url="https://media.discordapp.net/attachments/1342349362600218624/1459185809654808608/ChatGPT_Image_4_._2026_._15_58_32.png"
    )
    embed.add_field(name="Discord ID", value=str(discord_id), inline=False)
    embed.set_footer(
        text=f"Ивановы • Доложила {босс}",
        icon_url="https://media.discordapp.net/attachments/1342349362600218624/1459185809654808608/ChatGPT_Image_4_._2026_._15_58_32.png"
    )

    for f in fields:
        embed.add_field(name=f["name"], value=f["value"] or "—", inline=f.get("inline", False))

    channel = bot.get_channel(FORUM_CHANNEL_ID)
    if not channel:
        print("Форумный канал не найден")
        return

    try:
        thread, msg = await channel.create_thread(
            name=f"Заявка — {author_name}",
            embed=embed,
            auto_archive_duration=10080
        )
        print(f"Тред создан: {thread.name}")
    except Exception as e:
        print(f"Ошибка создания треда: {e}")
        return

    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    await msg.add_reaction("📞")

    # Выдаём роль "На проверке" сразу после создания треда
try:
    guild = bot.get_guild(thread.guild.id)
    if guild is None:
        print("Не удалось получить guild по ID из треда")
    else:
        member = await guild.fetch_member(discord_id)
        if member is None:
            print(f"Пользователь {discord_id} не найден на сервере")
        else:
            роль_проверка = guild.get_role(РОЛЬ_НА_ПРОВЕРКЕ)
            if роль_проверка:
                await member.add_roles(роль_проверка, reason="Новая заявка — на проверке")
                print(f"Роль 'На проверке' выдана {discord_id}")
            else:
                print("Роль 'На проверке' не найдена на сервере")
except Exception as e:
    print(f"Ошибка при выдаче роли 'На проверке': {e}")

    # ЛС заявителю
    try:
        await user.send(random.choice(РОФЛ_ПОЛУЧЕНО))
        print(f"Успешно написали в ЛС {discord_id}")
    except Exception as e:
        print(f"Не получилось написать в ЛС {discord_id}: {e}")


# === СОБЫТИЯ И КОМАНДЫ ===
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Леночка полностью готова → {bot.user}")


@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    msg = reaction.message
    if msg.author != bot.user:
        return

    embeds = msg.embeds
    if not embeds or "заявОчка" not in embeds[0].title.lower():
        return

    emoji = str(reaction.emoji)
    if emoji not in ["✅", "❌", "📞"]:
        return

    вердикт = {
        "✅": ("одобрена", random.choice(РОФЛ_ОДОБРЕНО)),
        "❌": ("отклонена", random.choice(РОФЛ_ОТКЛОНЕНО)),
        "📞": ("нужно уточнить", random.choice(РОФЛ_УТОЧНИТЬ))
    }[emoji]

    await msg.reply(f"{user.display_name} решил: {emoji} → заявка {вердикт[0]}")

    discord_id_str = None
    for field in embeds[0].fields:
        if field.name == "Discord ID":
            discord_id_str = field.value
            break

    if not discord_id_str or not discord_id_str.isdigit():
        print("Не нашли Discord ID в embed")
        return

    try:
    guild = bot.get_guild(msg.guild.id)
    if guild is None:
        print("Guild не найден в реакции")
    else:
        member = await guild.fetch_member(int(discord_id_str))
        if member is None:
            print(f"Пользователь {discord_id_str} не найден при реакции")
        else:
            # Снимаем "На проверке"
            роль_проверка = guild.get_role(РОЛЬ_НА_ПРОВЕРКЕ)
            if роль_проверка and роль_проверка in member.roles:
                await member.remove_roles(роль_проверка, reason=f"Заявка {вердикт[0]}")
                print(f"Снята роль проверки у {discord_id_str}")

            # Выдача при одобрении
            if emoji == "✅":
                роль_одобрено = guild.get_role(РОЛЬ_ОДОБРЕНО)
                if роль_одобрено:
                    await member.add_roles(роль_одобрено, reason="Заявка одобрена")
                    print(f"Выдана роль одобрено {discord_id_str}")

            await member.send(вердикт[1])
            print(f"Вердикт отправлен в ЛС {discord_id_str}")

except Exception as e:
    print(f"Ошибка при работе с ролями в реакции: {e}")


# === Запуск ===
def run_flask():
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
    print("Flask запущен")


threading.Thread(target=run_flask, daemon=True).start()

bot.run(TOKEN)

