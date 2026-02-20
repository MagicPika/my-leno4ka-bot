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

# Flask — принимает заявки
@app.route("/zayavka", methods=["POST"])
def принимать_заявку():
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {SECRET}":
        print("Неверный ключ")
        return jsonify({"error": "Неверный ключ"}), 401

    data = request.json or {}
    discord_id = data.get("discordId")
    author_name = data.get("authorName", "Без имени")
    fields = data.get("fields", [])

    print(f"Получена заявка: discordId={discord_id}, имя={author_name}")

    if not discord_id or not str(discord_id).isdigit():
        print("Нет нормального discordId")
        return jsonify({"error": "Нет нормального discordId"}), 400

    bot.loop.create_task(обработать_заявку(int(discord_id), author_name, fields))
    return jsonify({"status": "ok"}), 200


async def обработать_заявку(discord_id: int, author_name: str, fields: list):
    print(f"Обрабатываю заявку от {discord_id} ({author_name})")

    try:
        user = await bot.fetch_user(discord_id)
        avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
        print(f"Аватарка найдена для {discord_id}")
    except Exception as e:
        print(f"Не удалось взять аватарку {discord_id}: {e}")
        avatar_url = f"https://cdn.discordapp.com/embed/avatars/{discord_id % 6}.png"

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
        guild = bot.get_guild(thread.guild.id)
        if guild:
            member = await guild.fetch_member(discord_id)
            if member:
                роль_проверка = guild.get_role(РОЛЬ_НА_ПРОВЕРКЕ)
                if роль_проверка:
                    await member.add_roles(роль_проверка, reason="Новая заявка — на проверке")
                    print(f"Роль 'На проверке' выдана {discord_id}")
    except Exception as e:
        print(f"Ошибка выдачи роли 'На проверке': {e}")

    # ЛС заявителю
    try:
        await user.send(random.choice(РОФЛ_ПОЛУЧЕНО))
        print(f"Успешно написали в ЛС {discord_id}")

async def напомнить_через_сутки():
    await asyncio.sleep(60)

    try:
        свежий_msg = await thread.fetch_message(msg.id)
        реакции = свежий_msg.reactions
        has_reaction = any(r.emoji in ["✅", "❌", "📞"] for r in реакции)

        if not has_reaction:
            трэш = random.choice([
                "БЛЯТЬ, ВЫ ЧЁ, СПИТЕ?! Заявка висит сутки, Леночка уже в ярости 😡",
                "Эй, Кирилл и Иван, вы там живые вообще? Заявка пылится, как ваш член в штанах 💀",
                "24 часа прошло, а вы даже не пошевелились. Леночка начинает думать, что вы импотенты 🤡",
                "Напоминашка: заявка всё ещё ждёт. Если не отреагируете — Леночка придёт к вам в ЛС с ремнём 😈",
                "Вы серьёзно? Сутки прошло, а реакции ноль. Леночка разочарована в человечестве 🖕"
            ])
            await thread.send(трэш)
            print(f"Ебанутый пинок в тред {thread.name}")
    except:
        pass  # если тред удалён или ошибка — похуй

bot.loop.create_task(напомнить_через_сутки())
    except Exception as e:
        print(f"Не получилось написать в ЛС {discord_id}: {e}")


# === Запуск ===
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Леночка полностью готова → {bot.user}")


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
    except:
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

        # Вердикт в ЛС — твой словарь
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


# === Запуск ===
def run_flask():
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
    print("Flask запущен")


threading.Thread(target=run_flask, daemon=True).start()
bot.run(TOKEN)

