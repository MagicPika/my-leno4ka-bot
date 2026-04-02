import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Modal, TextInput, View
import os, random, sys, asyncio, threading, json
from flask import Flask, request, jsonify

app = Flask(__name__)

# ================= НАСТРОЙКИ =================
TOKEN = os.getenv("DISCORD_TOKEN")
FORUM_CHANNEL_ID = int(os.getenv("FORUM_CHANNEL_ID", "0")) # Default to 0, should be set in .env
SECRET = os.getenv("API_SECRET") # Moved to environment variable

РОЛЬ_НА_ПРОВЕРКЕ = int(os.getenv("ROLE_ON_CHECK_ID", "0"))
РОЛЬ_ОДОБРЕНО = int(os.getenv("ROLE_APPROVED_ID", "0"))

# ================= ЗАГРУЗКА ФРАЗ =================
def load_phrases():
    try:
        with open("phrases.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("phrases.json not found. Using default hardcoded phrases.")
        return {
            "received": [
                "Ооо, свеженькая заявОчка прилетела~ Леночка уже несёт боссам, сиди ровно, котик 😏💅",
                "Привеет, красавчик… Леночка увидела твою анкету и сердце ёкнуло 💓 Сейчас покажу наверх~",
                "Ух ты, кто-то решил вступить! Леночка в деле ✨ Жди, сейчас боссы будут в шоке от такого сокровища",
                "Заявочка от милоты! Леночка уже побежала к Кириллу/Ивану с горящими глазами ☕😘",
                "Ой-ой, какая интересная анкета… Леночка аж покраснела, читая 💕 Держись, сейчас понесут решать",
                "Минутку, солнышко, Леночка несёт твою заявку боссам! Не нервничай, я за тебя помолилась~ 🫶",
                "Твоя заявка у Леночки в ручках… Она уже дрожит от предвкушения, что скажут боссы 😳",
                "Прилетела заявочка! Леночка в восторге, сейчас покажу Кириллу/Ивану, пусть падают со стульев 🔥"
            ],
            "approved": [
                "Урааа~ 💕 Боссы сказали ДА! Заходи скорее, Леночка уже наливает тебе кофе и обнимает ☕🫂",
                "Одобрено! Леночка в полном восторге, ты прошёл, мой хороший! Теперь ты с нами навсегда 😘✨",
                "Кирилл/Иван дали добро! Добро пожаловать в нашу шайку, красавчик~ Леночка уже готовит тебе место рядом 💙",
                "Поздравляю, солнышко! Заявка прошла! Леночка прыгает от счастья и ждёт тебя с объятиями 🥳💕",
                "Одобренооо! Теперь ты официально наш~ Леночка в восторге и уже придумывает, как тебя баловать 😏❤️",
                "Боссы сказали «да»! Леночка кричит от радости! Заходи, мой звёздный, тут тебя все ждут 🌟",
                "Ты прошёл! Леночка чуть не расплакалась от счастья 💖 Теперь ты часть нашей семьи, любимый~",
                "Успех! Заявка одобрена! Леночка уже мысленно целует тебя в щёчку и тащит пить чай вместе 😘☕"
            ],
            "declined": [
                "Ой-ой… боссы сказали нет 😔 Но не грусти, Леночка всё равно тебя любит и обнимает крепко 💔🫂",
                "К сожалению, отказ… Леночка расстроилась вместе с тобой… Но ты всё равно милый, приходи попить чайку ☕💕",
                "Не прошли… Но Леночка уверена — это не конец, а просто поворот. Ты всё равно классный 😌",
                "Боссы сказали ❌… Леночка обнимает тебя сильно-сильно. Не переживай, ты всё равно звезда в её глазах 🌟",
                "Отказ… Леночка чуть не заплакала 😢 Но ты держись, мой хороший, следующий раз точно повезёт 💪❤️",
                "Увы, не зашло… Но Леночка всё равно считает тебя красавчиком. Заходи просто поболтать, ладно? 🫶",
                "Не одобрили… Леночка злится на боссов за тебя! Но ты не расстраивайся, ты всё равно лучший 😤💕",
                "Отклонено… Но Леночка шепчет тебе на ушко: «Ты всё равно самый-самый» 😘 Всё будет хорошо~"
            ],
            "clarify": [
                "Боссы хотят уточнить детали! Напиши в канал или в ЛС Леночке, я помогу всё разложить по полочкам 📞💕",
                "📞 Звоночек! Нужно кое-что уточнить, ждём тебя~ Леночка уже приготовила блокнотик и сердечки 😌",
                "Ой, боссам мало инфы… Напиши подробнее, пожалуйста, Леночка передаст всё-всё 💌",
                "Уточнение! Леночка просит тебя написать пару слов в тредик, чтобы боссы всё поняли до конца 🖊️❤️",
                "Боссы сказали «ещё инфы»~ Леночка на связи, пиши сюда или мне в ЛС, разберёмся вместе ☕",
                "📞 Нужно чуток уточнить! Леночка ждёт твоих слов, не стесняйся, мой хороший 🌸",
                "Боссы любопытные, хотят больше деталей! Пиши в тред, Леночка уже держит ручку наготове ✍️💕",
                "Уточняем! Леночка просит тебя добавить пару строчек, чтобы всё стало идеально 😘"
            ]
        }

PHRASES = load_phrases()

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
            try:
                await self.thread.edit(applied_tags=[tag])
            except discord.Forbidden:
                print(f"Нет прав для установки тега {tag_name} в треде {self.thread.id}")

    async def send_dm_safely(self, user: discord.User, message_content: str):
        try:
            await user.send(message_content)
        except discord.Forbidden:
            print(f"Не удалось отправить ЛС пользователю {user.id}. ЛС закрыты.")
        except Exception as e:
            print(f"Ошибка при отправке ЛС пользователю {user.id}: {e}")

    @discord.ui.button(label="✅ Одобрить", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = guild.get_member(self.user.id)

        if member:
            try:
                role_check = guild.get_role(РОЛЬ_НА_ПРОВЕРКЕ)
                if role_check and role_check in member.roles:
                    await member.remove_roles(role_check)

                role_ok = guild.get_role(РОЛЬ_ОДОБРЕНО)
                if role_ok:
                    await member.add_roles(role_ok)
            except discord.Forbidden:
                print(f"Нет прав для изменения ролей пользователя {member.id}")
                await interaction.response.send_message("Недостаточно прав для изменения ролей.", ephemeral=True)
                return
            except Exception as e:
                print(f"Ошибка при изменении ролей пользователя {member.id}: {e}")
                await interaction.response.send_message("Произошла ошибка при изменении ролей.", ephemeral=True)
                return

        await self.send_dm_safely(self.user, random.choice(PHRASES.get("approved", [])))
        await self.поставить_тег("Одобрена")
        await interaction.response.send_message("Заявка одобрена", ephemeral=True)
        self.stop()

    @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.send_dm_safely(self.user, random.choice(PHRASES.get("declined", [])))
        await self.поставить_тег("Отклонена")
        await interaction.response.send_message("Заявка отклонена", ephemeral=True)
        self.stop()

    @discord.ui.button(label="📞 Уточнить", style=discord.ButtonStyle.secondary)
    async def clarify(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.send_dm_safely(self.user, random.choice(PHRASES.get("clarify", [])))
        await self.поставить_тег("На уточнении")
        await interaction.response.send_message("Запрошено уточнение", ephemeral=True)


# ================= СОЗДАНИЕ ЗАЯВКИ =================
async def обработать_заявку(discord_id: int, author_name: str, fields: list):
    try:
        user = await bot.fetch_user(discord_id)
    except discord.NotFound:
        print(f"Пользователь с ID {discord_id} не найден.")
        return
    except Exception as e:
        print(f"Ошибка при получении пользователя {discord_id}: {e}")
        return

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
        print(f"Канал с ID {FORUM_CHANNEL_ID} не является форумным каналом.")
        return

    try:
        thread_with_msg = await channel.create_thread(
            name=f"Заявка-{author_name}-{discord_id}", # Добавлен discord_id для уникальности
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
            try:
                await member.add_roles(роль)
            except discord.Forbidden:
                print(f"Нет прав для выдачи роли {РОЛЬ_НА_ПРОВЕРКЕ} пользователю {member.id}")
            except Exception as e:
                print(f"Ошибка при выдаче роли {РОЛЬ_НА_ПРОВЕРКЕ} пользователю {member.id}: {e}")

        await КнопкиЗаявки(user, thread).send_dm_safely(user, random.choice(PHRASES.get("received", [])))

    except discord.Forbidden:
        print(f"Нет прав для создания треда или отправки сообщений в канал {FORUM_CHANNEL_ID}")
    except Exception as e:
        print(f"Ошибка при обработке заявки: {e}")

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

            # Ищем тред по уникальному имени, включающему discord_id
            target_thread = None
            for thread in forum.threads:
                if thread.name.startswith(f"Заявка-{message.author.name}-{user_id}") or thread.name.startswith(f"Заявка-{user_id}"):
                    target_thread = thread
                    break

            if target_thread and not target_thread.archived:
                try:
                    await target_thread.send(
                        f"📩 Ответ от {message.author.mention}:\n{message.content}"
                    )
                    # Возвращаем тег "На проверке"
                    tag = next((t for t in forum.available_tags if t.name == "На проверке"), None)
                    if tag:
                        try:
                            await target_thread.edit(applied_tags=[tag])
                        except discord.Forbidden:
                            print(f"Нет прав для установки тега 'На проверке' в треде {target_thread.id}")
                except discord.Forbidden:
                    print(f"Нет прав для отправки сообщения в тред {target_thread.id}")
                except Exception as e:
                    print(f"Ошибка при пересылке ЛС в тред {target_thread.id}: {e}")
                return

    await bot.process_commands(message)

# ================= FLASK =================
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "OK"}), 200

@app.route("/zayavka", methods=["POST"])
def принимать_заявку():
    auth = request.headers.get("Authorization")
    if SECRET is None or auth != f"Bearer {SECRET}":
        return jsonify({"error": "Неверный ключ или ключ не установлен"}), 401

    data = request.json or {}
    
    discord_id_raw = data.get("discordId")
    if not discord_id_raw or not str(discord_id_raw).isdigit():
        return jsonify({"error": "Неверный или отсутствующий discordId"}), 400
    discord_id = int(discord_id_raw)

    author_name = data.get("authorName", "Без имени")
    fields = data.get("fields", [])

    # Использование asyncio.run_coroutine_threadsafe для безопасного вызова асинхронной функции из другого потока
    try:
        asyncio.run_coroutine_threadsafe(обработать_заявку(discord_id, author_name, fields), bot.loop)
    except RuntimeError as e:
        print(f"Ошибка при планировании корутины: {e}")
        return jsonify({"error": "Ошибка сервера при обработке заявки"}), 500

    return jsonify({"status": "ok"}), 200

def run_flask():
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)

# Запуск Flask в отдельном потоке
threading.Thread(target=run_flask, daemon=True).start()

# ================= ЗАПУСК =================
if TOKEN is None:
    print("Ошибка: Токен Discord не установлен. Установите переменную окружения DISCORD_TOKEN.")
    sys.exit(1)

bot.run(TOKEN)
