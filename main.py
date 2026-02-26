# main.py
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Modal, TextInput, View
import os, random, sys, asyncio, threading
from flask import Flask, request, jsonify

app = Flask(__name__)

# ================= НАСТРОЙКИ =================
TOKEN = os.getenv("DISCORD_TOKEN")
FORUM_CHANNEL_ID = 1458885875692732438
SECRET = "2122428Matros"

РОЛЬ_НА_ПРОВЕРКЕ = 1474320899598581791
РОЛЬ_ОДОБРЕНО = 1457319043315929267

# ================= РОФЛЫ =================
РОФЛ_ПОЛУЧЕНО = [
        "Ооо, свеженькая заявОчка прилетела~ Леночка уже несёт боссам, сиди ровно, котик 😏💅",
    "Привеет, красавчик… Леночка увидела твою анкету и сердце ёкнуло 💓 Сейчас покажу наверх~",
    "Ух ты, кто-то решил вступить! Леночка в деле ✨ Жди, сейчас боссы будут в шоке от такого сокровища",
    "Заявочка от милоты! Леночка уже побежала к Кириллу/Ивану с горящими глазами ☕😘",
    "Ой-ой, какая интересная анкета… Леночка аж покраснела, читая 💕 Держись, сейчас понесут решать",
    "Минутку, солнышко, Леночка несёт твою заявку боссам! Не нервничай, я за тебя помолилась~ 🫶",
    "Твоя заявка у Леночки в ручках… Она уже дрожит от предвкушения, что скажут боссы 😳",
    "Прилетела заявочка! Леночка в восторге, сейчас покажу Кириллу/Ивану, пусть падают со стульев 🔥"
]
РОФЛ_ОДОБРЕНО = [
        "Урааа~ 💕 Боссы сказали ДА! Заходи скорее, Леночка уже наливает тебе кофе и обнимает ☕🫂",
    "Одобрено! Леночка в полном восторге, ты прошёл, мой хороший! Теперь ты с нами навсегда 😘✨",
    "Кирилл/Иван дали добро! Добро пожаловать в нашу шайку, красавчик~ Леночка уже готовит тебе место рядом 💙",
    "Поздравляю, солнышко! Заявка прошла! Леночка прыгает от счастья и ждёт тебя с объятиями 🥳💕",
    "Одобренооо! Теперь ты официально наш~ Леночка в восторге и уже придумывает, как тебя баловать 😏❤️",
    "Боссы сказали «да»! Леночка кричит от радости! Заходи, мой звёздный, тут тебя все ждут 🌟",
    "Ты прошёл! Леночка чуть не расплакалась от счастья 💖 Теперь ты часть нашей семьи, любимый~",
    "Успех! Заявка одобрена! Леночка уже мысленно целует тебя в щёчку и тащит пить чай вместе 😘☕"
]
РОФЛ_ОТКЛОНЕНО = [
        "Ой-ой… боссы сказали нет 😔 Но не грусти, Леночка всё равно тебя любит и обнимает крепко 💔🫂",
    "К сожалению, отказ… Леночка расстроилась вместе с тобой… Но ты всё равно милый, приходи попить чайку ☕💕",
    "Не прошли… Но Леночка уверена — это не конец, а просто поворот. Ты всё равно классный 😌",
    "Боссы сказали ❌… Леночка обнимает тебя сильно-сильно. Не переживай, ты всё равно звезда в её глазах 🌟",
    "Отказ… Леночка чуть не заплакала 😢 Но ты держись, мой хороший, следующий раз точно повезёт 💪❤️",
    "Увы, не зашло… Но Леночка всё равно считает тебя красавчиком. Заходи просто поболтать, ладно? 🫶",
    "Не одобрили… Леночка злится на боссов за тебя! Но ты не расстраивайся, ты всё равно лучший 😤💕",
    "Отклонено… Но Леночка шепчет тебе на ушко: «Ты всё равно самый-самый» 😘 Всё будет хорошо~"
]
РОФЛ_УТОЧНИТЬ = [    "Боссы хотят уточнить детали! Напиши в канал или в ЛС Леночке, я помогу всё разложить по полочкам 📞💕",
    "📞 Звоночек! Нужно кое-что уточнить, ждём тебя~ Леночка уже приготовила блокнотик и сердечки 😌",
    "Ой, боссам мало инфы… Напиши подробнее, пожалуйста, Леночка передаст всё-всё 💌",
    "Уточнение! Леночка просит тебя написать пару слов в тредик, чтобы боссы всё поняли до конца 🖊️❤️",
    "Боссы сказали «ещё инфы»~ Леночка на связи, пиши сюда или мне в ЛС, разберёмся вместе ☕",
    "📞 Нужно чуток уточнить! Леночка ждёт твоих слов, не стесняйся, мой хороший 🌸",
    "Боссы любопытные, хотят больше деталей! Пиши в тред, Леночка уже держит ручку наготове ✍️💕",
    "Уточняем! Леночка просит тебя добавить пару строчек, чтобы всё стало идеально 😘"]

# ================= БОТ =================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Бот запущен: {bot.user}")
    await bot.tree.sync()

# ================= КНОПКИ =================
class КнопкиЗаявки(View):
    def __init__(self, user: discord.User, thread: discord.Thread):
        super().__init__(timeout=None)
        self.user = user
        self.thread = thread

    async def поставить_тег(self, tag_name: str):
        forum = self.thread.parent
        if not isinstance(forum, discord.ForumChannel):
            return

        tag = next((t for t in forum.available_tags if t.name == tag_name), None)
        if tag:
            await self.thread.edit(applied_tags=[tag])

    @discord.ui.button(label="✅ Одобрить", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = guild.get_member(self.user.id)

        if member:
            role_check = guild.get_role(РОЛЬ_НА_ПРОВЕРКЕ)
            if role_check and role_check in member.roles:
                await member.remove_roles(role_check)

            role_ok = guild.get_role(РОЛЬ_ОДОБРЕНО)
            if role_ok:
                await member.add_roles(role_ok)

        await self.user.send(random.choice(РОФЛ_ОДОБРЕНО))
        await self.поставить_тег("Одобрена")
        await interaction.response.send_message("Заявка одобрена", ephemeral=True)
        self.stop()

    @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.user.send(random.choice(РОФЛ_ОТКЛОНЕНО))
        await self.поставить_тег("Отклонена")
        await interaction.response.send_message("Заявка отклонена", ephemeral=True)
        self.stop()

    @discord.ui.button(label="📞 Уточнить", style=discord.ButtonStyle.secondary)
    async def clarify(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.user.send(random.choice(РОФЛ_УТОЧНИТЬ))
        await self.поставить_тег("На уточнении")
        await interaction.response.send_message("Запрошено уточнение", ephemeral=True)


# ================= СОЗДАНИЕ ЗАЯВКИ =================
async def обработать_заявку(discord_id: int, author_name: str, fields: list):
    user = await bot.fetch_user(discord_id)

    embed = discord.Embed(
        title=f"Заявка от {author_name}",
        color=0x85144b,
        timestamp=discord.utils.utcnow()
    )

    # Discord ID отдельным полем
    embed.add_field(
        name="Discord ID",
        value=f"<@{discord_id}> (`{discord_id}`)",
        inline=False
    )

    for f in fields:
        embed.add_field(
            name=f.get("name", "—"),
            value=f.get("value", "—"),
            inline=False
        )

    channel = bot.get_channel(FORUM_CHANNEL_ID)
    if not isinstance(channel, discord.ForumChannel):
        return

    thread_with_msg = await channel.create_thread(
        name=f"Заявка-{author_name}",
        embed=embed,
        auto_archive_duration=10080
    )

    thread = thread_with_msg.thread

    view = КнопкиЗаявки(user, thread)
    await thread.send("Выберите действие:", view=view)

    guild = bot.get_guild(thread.guild.id)
    member = await guild.fetch_member(discord_id)

    роль = guild.get_role(РОЛЬ_НА_ПРОВЕРКЕ)
    if роль:
        await member.add_roles(роль)

    await user.send(random.choice(РОФЛ_ПОЛУЧЕНО))

# ================= ПЕРЕСЫЛКА ЛС =================
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if isinstance(message.channel, discord.DMChannel):
        user_id = message.author.id

        for guild in bot.guilds:
            forum = guild.get_channel(FORUM_CHANNEL_ID)
            if not isinstance(forum, discord.ForumChannel):
                continue

            for thread in forum.threads:
                if thread.archived:
                    continue

                if thread.name.startswith(f"Заявка-{user_id}-"):
                    await thread.send(
                        f"📩 Ответ от {message.author.mention}:\n{message.content}"
                    )
                     # Возвращаем тег "На проверке"
                    forum = thread.parent
                    tag = next((t for t in forum.available_tags if t.name == "На проверке"), None)
                    if tag:
                        await thread.edit(applied_tags=[tag])
                
                    return

    await bot.process_commands(message)

# ================= FLASK =================
@app.route("/zayavka", methods=["POST"])
def принимать_заявку():
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {SECRET}":
        return jsonify({"error": "Неверный ключ"}), 401

    data = request.json or {}
    discord_id = int(data.get("discordId"))
    author_name = data.get("authorName", "Без имени")
    fields = data.get("fields", [])

    bot.loop.create_task(обработать_заявку(discord_id, author_name, fields))
    return jsonify({"status": "ok"}), 200

def run_flask():
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)

threading.Thread(target=run_flask, daemon=True).start()

# ================= ЗАПУСК =================
bot.run(TOKEN)







