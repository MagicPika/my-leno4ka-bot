import discord
from discord.ext import commands
import os
from flask import Flask, request, jsonify
import threading
import random

app = Flask(name)

# === НАСТРОЙКИ ===
TOKEN = os.getenv("DISCORD_TOKEN")
FORUM_CHANNEL_ID = 123456789012345678     # ← твой ID форумного канала
SECRET = "твой_секретный_ключ_из_формы"   # ← меняй обязательно

РОЛЬ_НА_ПРОВЕРКЕ = 111111111111111111     # ← ID роли "На проверке"
РОЛЬ_ОДОБРЕНО    = 222222222222222222     # ← ID роли "Одобрен"

РОФЛ_ПОЛУЧЕНО = [
    "Привеет~ 💕 Леночка увидела твою заявку и уже понесла боссам! Жди вердикта, не скучай ☕️",
    "Ой, какая сочная заявОчка! Леночка в восторге, сейчас покажу Кириллу/Ивану 😘",
    "Всё-всё, поняла! Заявка ушла наверх. Держи пальчики скрещенными 💋",
    "Твоя заявка принята, котик! Леночка доложила, теперь только ждать~ ✨"
]

РОФЛ_ОДОБРЕНО = [
    "Урааа~ 💕 Твоя заявка одобрена! Заходи скорее, Леночка уже наливает кофе ☕️",
    "Боссы сказали ДА! Добро пожаловать, солнышко 😘",
    "Одобрено! Леночка в восторге, ты прошёл~ ❤️"
]

РОФЛ_ОТКЛОНЕНО = [
    "Ой-ой… боссы сказали нет 😔 Но не грусти, Леночка всё равно тебя любит 💔",
    "К сожалению, отказ… Но в следующий раз Леночка за тебя лучше замолвит словечко 😉",
    "Не прошли… Но ты милый, приходи попить чайку с Леночкой ☕️"
]

РОФЛ_УТОЧНИТЬ = [
    "Боссы хотят уточнить детали! Напиши в канал или в ЛС Леночке 📞",
    "📞 Звоночек! Нужно кое-что уточнить, ждём тебя~",
    "Ой, боссам мало инфы… Напиши подробнее, пожалуйста 💕"
]

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
        "Заявочка от красавчика! Сейчас покажу Кириллу/Ивану ☕️",
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

    # Роль "На проверке"
    try:
        роль_проверка = thread.guild.get_role(РОЛЬ_НА_ПРОВЕРКЕ)
        if роль_проверка:
            await user.add_roles(роль_проверка, reason="Новая заявка — на проверке")
            print(f"Выдана роль 'На проверке' пользователю {discord_id}")
    except Exception as e:
        print(f"Ошибка выдачи роли 'На проверке': {e}")

    # ЛС заявителю
    try:
        await user.send(random.choice(РОФЛ_ПОЛУЧЕНО))
        print(f"Успешно написали в ЛС {discord_id}")
    except Exception as e:
        print(f"Не получилось написать в ЛС {discord_id}: {e}")


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
        member = await msg.guild.fetch_member(int(discord_id_str))
        if not member:
            return

        роль_проверка = msg.guild.get_role(РОЛЬ_НА_ПРОВЕРКЕ)
        if роль_проверка and роль_проверка in member.roles:
            await member.remove_roles(роль_проверка, reason=f"Заявка {вердикт[0]}")
            print(f"Снята роль 'На проверке' у {discord_id_str}")

        if emoji == "✅":
            роль_одобрено = msg.guild.get_role(РОЛЬ_ОДОБРЕНО)
            if роль_одобрено:
                await member.add_roles(роль_одобрено, reason="Заявка одобрена")
                print(f"Выдана роль 'Одобрен' пользователю {discord_id_str}")

        await member.send(вердикт[1])
        print(f"Вердикт отправлен в ЛС {discord_id_str}")

    except Exception as e:
        print(f"Ошибка при обработке реакции: {e}")


# === Запуск ===
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Леночка полностью готова → {bot.user}")


def run_flask():
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
    print("Flask запущен")


# Запускаем Flask в фоне
threading.Thread(target=run_flask, daemon=True).start()

# Запускаем бота последним
bot.run(TOKEN)
