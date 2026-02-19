# main.py
import discord
from discord.ext import commands
import os
from flask import Flask, request, jsonify
import threading
import random

app = Flask(__name__)

# === НАСТРОЙКИ (меняй здесь всё, что нужно) ===
TOKEN = os.getenv("DISCORD_TOKEN")
FORUM_CHANNEL_ID = 1458881043653197896     # ← реальный ID форумного канала
SECRET = "2122428Matros"  # ← свой секретный ключ

РОЛЬ_НА_ПРОВЕРКЕ = 1473913094697783380     # ← ID роли "На проверке"
РОЛЬ_ОДОБРЕНО    = 1473913198016069642     # ← ID роли "Одобрен" или "Участник"

# Рофл-фразы в ЛС при получении заявки
РОФЛ_ПОЛУЧЕНО = [
    "Привеет~ 💕 Леночка увидела твою заявку и уже понесла боссам! Жди вердикта, не скучай ☕",
    "Ой, какая сочная заявОчка! Леночка в восторге, сейчас покажу Кириллу/Ивану 😘",
    "Всё-всё, поняла! Заявка ушла наверх. Держи пальчики скрещенными 💋",
    "Твоя заявка принята, котик! Леночка доложила, теперь только ждать~ ✨"
]

# Рофл при реакции
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


# === Запуск бота ===
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
