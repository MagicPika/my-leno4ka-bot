import discord
from discord.ext import commands
import os
from flask import Flask, request, jsonify
import threading
import random

app = Flask(__name__)

# Твои настройки (можно менять)
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 123456789012345678         # ← ID твоего форумного канала
SECRET = "леночка_очень_секретный_2026"  # придумывай длинный и сложный

РОФЛ = [
    "Ой-ой, свеженькая заявОчка прилетела~ 💅",
    "Минутку, котик, Леночка уже несёт боссам! 😏",
    "Заявочка от красавчика! Сейчас покажу Кириллу/Ивану ☕",
    "Ух ты, кто-то решил вступить! Леночка в деле ✨"
]

@app.route("/zayavka", methods=["POST"])
def принимать_заявку():
    if request.headers.get("Authorization") != f"Bearer {SECRET}":
        return jsonify({"error": "Неверный ключ"}), 401

    data = request.json or {}
    discord_id = data.get("discordId")
    author_name = data.get("authorName", "Без имени")
    fields = data.get("fields", [])
    mention = data.get("mention", "Не указан")
    ic = data.get("ic", "Не указан")

    if not discord_id or not discord_id.isdigit():
        return jsonify({"error": "Нет нормального discordId"}), 400

    bot.loop.create_task(отправить_заявку(int(discord_id), author_name, fields, mention, ic))
    return jsonify({"status": "Леночка уже побежала"}), 200


async def отправить_заявку(discord_id: int, author_name: str, fields: list, mention: str, ic: str):
    try:
        user = await bot.fetch_user(discord_id)
        avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
    except:
        avatar_url = f"https://cdn.discordapp.com/embed/avatars/{discord_id % 6}.png"

    босс = random.choice(["Кирилл Иванов", "Иван Иванов"])
    рофл_заголовок = random.choice(РОФЛ)

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
    embed.set_footer(
        text=f"Ивановы • Доложила {босс}",
        icon_url="https://media.discordapp.net/attachments/1342349362600218624/1459185809654808608/ChatGPT_Image_4_._2026_._15_58_32.png"
    )

    for f in fields:
        embed.add_field(name=f["name"], value=f["value"] or "—", inline=f.get("inline", False))

    channel = bot.get_channel(CHANNEL_ID)
    if channel and channel.type == discord.ChannelType.forum:
        thread = await channel.create_thread(
            name=f"Заявка — {author_name}",
            content=None,
            embed=embed,
            auto_archive_duration=10080  # 7 дней
        )
        msg = thread.message
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        await msg.add_reaction("📞")
    else:
        # Если вдруг не форум — просто постим
        await channel.send(embed=embed)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print("Леночка готова принимать заявки из формы")


def запустить_flask():
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)


threading.Thread(target=запустить_flask, daemon=True).start()

bot.run(TOKEN)
