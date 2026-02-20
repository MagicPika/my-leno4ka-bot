# main.py
import discord
from discord.ext import commands
import os
from flask import Flask, request, jsonify
import threading
import random
import sys
import asyncio

app = Flask(__name__)

# === НАСТРОЙКИ ===
TOKEN = os.getenv("DISCORD_TOKEN")
FORUM_CHANNEL_ID = 1458881043653197896
SECRET = "2122428Matros"

РОЛЬ_НА_ПРОВЕРКЕ = 1473913094697783380
РОЛЬ_ОДОБРЕНО = 1473913198016069642

РОФЛ_ПОЛУЧЕНО = [
    "Привеет~ 💕 Леночка увидела твою заявку и уже понесла боссам! Жди вердикта, не скучай ☕",
    "Ой, какая сочная заявОчка! Леночка в восторге, сейчас покажу Кириллу/Ивану 😘"
]

РОФЛ_ОДОБРЕНО = [
    "Урааа~ 💕 Твоя заявка одобрена! Заходи скорее, Леночка уже наливает кофе ☕",
    "Боссы сказали ДА! Добро пожаловать, солнышко 😘"
]

РОФЛ_ОТКЛОНЕНО = [
    "Ебошь отседа",
    "Уебись тапком блять"
]

РОФЛ_УТОЧНИТЬ = [
    "Пеер",
    "пиши"
]

# Flask — принимает заявки из формы
@app.route("/zayavka", methods=["POST"])
def принимать_заявку():
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {SECRET}":
        print("Неверный ключ")
        sys.stdout.flush()
        return jsonify({"error": "Неверный ключ"}), 401

    data = request.json or {}
    discord_id = data.get("discordId")
    author_name = data.get("authorName", "Без имени")
    fields = data.get("fields", [])

    print(f"Получена заявка: discordId={discord_id}, имя={author_name}")
    sys.stdout.flush()

    if not discord_id or not str(discord_id).isdigit():
        print("Нет нормального discordId")
        sys.stdout.flush()
        return jsonify({"error": "Нет нормального discordId"}), 400

    bot.loop.create_task(обработать_заявку(int(discord_id), author_name, fields))
    return jsonify({"status": "ok"}), 200


# Основная обработка заявки
async def обработать_заявку(discord_id: int, author_name: str, fields: list):
    print(f"Обрабатываю заявку от {discord_id} ({author_name})")
    sys.stdout.flush()

    try:
        user = await bot.fetch_user(discord_id)
        avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
        print(f"Аватарка найдена для {discord_id}")
    except Exception as e:
        print(f"Не удалось взять аватарку {discord_id}: {e}")
        avatar_url = f"https://cdn.discordapp.com/embed/avatars/{discord_id % 6}.png"
    sys.stdout.flush()

    embed = discord.Embed(
        title="Заявка от " + author_name,
        description="Ожидает решения боссов",
        color=13369344,
        timestamp=discord.utils.utcnow()
    )
    embed.set_thumbnail(url=avatar_url)
    embed.add_field(name="Discord ID", value=str(discord_id), inline=False)

    for f in fields:
        embed.add_field(name=f["name"], value=f["value"] or "—", inline=f.get("inline", False))

    channel = bot.get_channel(FORUM_CHANNEL_ID)
    if not channel:
        print("Форумный канал не найден")
        sys.stdout.flush()
        return

    try:
        thread, msg = await channel.create_thread(
            name=f"Заявка — {author_name}",
            embed=embed,
            auto_archive_duration=10080
        )
        print(f"Тред создан: {thread.name}")
        sys.stdout.flush()
    except Exception as e:
        print(f"Ошибка создания треда: {e}")
        sys.stdout.flush()
        return

    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    await msg.add_reaction("📞")

    # Роль "На проверке"
    try:
        guild = bot.get_guild(thread.guild.id)
        if guild:
            member = await guild.fetch_member(discord_id)
            if member:
                роль_проверка = guild.get_role(РОЛЬ_НА_ПРОВЕРКЕ)
                if роль_проверка:
                    await member.add_roles(роль_проверка, reason="Новая заявка — на проверке")
                    print(f"Роль 'На проверке' выдана {discord_id}")
                    sys.stdout.flush()
    except Exception as e:
        print(f"Ошибка выдачи роли 'На проверке': {e}")
        sys.stdout.flush()

    # ЛС заявителю
    try:
        await user.send(random.choice(РОФЛ_ПОЛУЧЕНО))
        print(f"Успешно написали в ЛС {discord_id}")
        sys.stdout.flush()
    except Exception as e:
        print(f"Не получилось написать в ЛС {discord_id}: {e}")
        sys.stdout.flush()
    async def ебанутый_таймер_истерики():
        await asyncio.sleep(30)  # 24 часа = первые сутки тишины

        уровни_ебанутости = [
            ("Милый пинок", [
                "Боссики~ Уже сутки прошло, а реакции нет... Леночка грустит 😔",
                "Эй, не спите там, заявка ждёт вашего внимания~ ☕💕"
            ]),
            ("Средний троллинг", [
                "Серьёзно? 30 часов тишины. Вы там вообще живые или уже сдохли от лени? 🤡",
                "Леночка начинает подозревать, что вы просто дрочите в сторонке вместо работы 😏"
            ]),
            ("Полный пиздец", [
                "БЛЯТЬ ВЫ ЧЁ, МЁРТВЫЕ?! Заявка висит вторые сутки, а вы даже палец о палец не ударили! 😡",
                "Если через 6 часов не отреагируете — Леночка придёт к вам в ЛС с ножом и заставит одобрить или отклонить, суки ленивые 🖕",
                "Я уже представляю, как вы сидите и думаете 'потом посмотрим'. ПОТОМ БЛЯТЬ НЕ БУДЕТ, РЕАГИРУЙТЕ НАХУЙ!"
            ])
        ]

        for уровень, фразы in уровни_ебанутости:
            await asyncio.sleep(6)  # каждые 6 часов новый уровень ада

            try:
                свежий_msg = await thread.fetch_message(msg.id)
                реакции = свежий_msg.reactions
                has_reaction = any(r.emoji in ["✅", "❌", "📞"] for r in реакции)

                if has_reaction:
                    print("Реакция появилась — истерика отменяется")
                    await thread.send("Ой, наконец-то... Леночка успокаивается 😌")
                    return

                трэш = random.choice(фразы)
                await thread.send(трэш)
                print(f"Ебанутый уровень {уровень} отправлен: {трэш[:30]}...")
            except Exception as e:
                print(f"Ошибка в ебанутом таймере: {e}")
                return

        # Финальный пиздец через 72 часа
        await thread.send(f"<@924956705756971028> <@695943956856307744> "Всё, Леночка уходит нахуй. Боссы - ленивые долбоёбы, заявка закрыта навсегда 🖕")
        await thread.edit(archived=True, locked=True)
        print("Тред заархивирован за бездействие боссов")

    # Запускаем этот ад в фоне
    bot.loop.create_task(ебанутый_таймер_истерики())


# === Запуск ===
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Леночка полностью готова → {bot.user}")
    sys.stdout.flush()


@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return

    emoji = str(payload.emoji)
    if emoji not in ["✅", "❌", "📞"]:
        return

    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        print("Guild не найден в реакции")
        return

    channel = bot.get_channel(payload.channel_id)
    if channel is None:
        return

    try:
        message = await channel.fetch_message(payload.message_id)
    except Exception as e:
        print(f"Не удалось взять сообщение: {e}")
        return

    if not message.embeds:
        return

    embed = message.embeds[0]

    discord_id_str = None
    for field in embed.fields:
        if field.name == "Discord ID":
            discord_id_str = field.value
            break

    if not discord_id_str or not discord_id_str.isdigit():
        print("Не нашли Discord ID в embed")
        return

    try:
        member = await guild.fetch_member(int(discord_id_str))
        if not member:
            print(f"Member не найден для {discord_id_str}")
            return

        роль_проверка = guild.get_role(РОЛЬ_НА_ПРОВЕРКЕ)
        if роль_проверка and роль_проверка in member.roles:
            await member.remove_roles(роль_проверка, reason="Заявка обработана")
            print(f"Снята роль проверки у {discord_id_str}")

        if emoji == "✅":
            роль_одобрено = guild.get_role(РОЛЬ_ОДОБРЕНО)
            if роль_одобрено:
                await member.add_roles(роль_одобрено, reason="Заявка одобрена")
                print(f"Выдана роль одобрено {discord_id_str}")

        вердикт_текст = {
            "✅": random.choice(РОФЛ_ОДОБРЕНО),
            "❌": random.choice(РОФЛ_ОТКЛОНЕНО),
            "📞": random.choice(РОФЛ_УТОЧНИТЬ)
        }[emoji]

        await message.reply(f"{payload.member.display_name} решил: {emoji} → заявка обработана")

        await member.send(вердикт_текст)
        print(f"Вердикт отправлен в ЛС: {вердикт_текст[:30]}...")

    except Exception as e:
        print(f"Ошибка реакции: {e}")
        sys.stdout.flush()


# === Запуск ===
def run_flask():
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
    print("Flask запущен")
    sys.stdout.flush()


threading.Thread(target=run_flask, daemon=True).start()
bot.run(TOKEN)




