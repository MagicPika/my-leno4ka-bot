import discord
from discord.ext import commands
import os, random, asyncio, threading
from flask import Flask, request, jsonify

app = Flask(__name__)

TOKEN = os.getenv("DISCORD_TOKEN")
FORUM_CHANNEL_ID = 1458885875692732438
SECRET = os.getenv("SECRET")
SECRETARY_AVATAR = "https://media.discordapp.net/attachments/1342349362600218624/1491002108848115712/ChatGPT_Image_20_._2026_._09_40_12.png?ex=69d61b6c&is=69d4c9ec&hm=149507a3a74a7ad85fd24b8384685221bd4d9395d83799eb4ce84738f2d2caf3&=&format=webp&quality=lossless&width=638&height=958"

РОЛЬ_НА_ПРОВЕРКЕ = 1474320899598581791
РОЛЬ_ОДОБРЕНО = 1457319043315929267

# ================= РОФЛЫ =================
РОФЛ_ПОЛУЧЕНО = [
    "Ой~ новая заявочка! 💕 Леночка уже несёт боссам.",
    "Ммм~ интересненько… Леночка читает ☕"
]

РОФЛ_ОДОБРЕНО = [
    "Ура~ 💕 Боссы сказали да!",
    "Добро пожаловать~ ✨ Леночка рада!"
]

РОФЛ_ОТКЛОНЕНО = [
    "Ой… пока не получилось 😔",
    "Не в этот раз, но Леночка верит в тебя 💔"
]

РОФЛ_УТОЧНИТЬ = [
    "Леночке нужно чуть больше информации 💕",
    "Уточни детали, пожалуйста ✨"
]

# ================= BOT =================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= КНОПКИ =================
class КнопкиЗаявки(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id

    async def get_member(self, interaction):
        return interaction.guild.get_member(self.user_id)

    @discord.ui.button(label="✅ Одобрить", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = await self.get_member(interaction)

        if member:
            role_check = interaction.guild.get_role(РОЛЬ_НА_ПРОВЕРКЕ)
            if role_check and role_check in member.roles:
                await member.remove_roles(role_check)

            role_ok = interaction.guild.get_role(РОЛЬ_ОДОБРЕНО)
            if role_ok:
                await member.add_roles(role_ok)

            try:
                await member.send(random.choice(РОФЛ_ОДОБРЕНО))
            except:
                pass

        await interaction.response.send_message(
            f"✅ {member.mention} одобрен",
            ephemeral=True
        )

    @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = await self.get_member(interaction)

        if member:
            try:
                await member.send(random.choice(РОФЛ_ОТКЛОНЕНО))
            except:
                pass

        await interaction.response.send_message(
            f"❌ {member.mention} отклонён",
            ephemeral=True
        )

    @discord.ui.button(label="📞 Уточнить", style=discord.ButtonStyle.secondary)
    async def clarify(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = await self.get_member(interaction)

        if member:
            try:
                await member.send(random.choice(РОФЛ_УТОЧНИТЬ))
            except:
                pass

        await interaction.response.send_message(
            f"📞 Уточнение у {member.mention}",
            ephemeral=True
        )

# ================= ФОРМА =================
@app.route("/zayavka", methods=["POST"])
def принять():
    if request.headers.get("Authorization") != f"Bearer {SECRET}":
        return {"error": "no auth"}, 401

    data = request.json
    bot.loop.create_task(process(data))
    return {"ok": True}

# ================= ОБРАБОТКА =================
async def process(data):
    discord_id = int(data["discordId"])
    author_name = data.get("authorName", "Без имени")
    fields = data.get("fields", [])

    guild = bot.guilds[0]

    # Получаем участника (для аватарки и ролей)
    try:
        member = await guild.fetch_member(discord_id)
        avatar = member.display_avatar.url
        mention = member.mention
    except:
        user = await bot.fetch_user(discord_id)
        avatar = user.display_avatar.url
        mention = f"<@{discord_id}>"

    # ================= EMBED =================
    embed = discord.Embed(
        title=f"Заявка от {author_name}",
        description="Ожидает решения боссов",
        color=0x2b2d31
    )

    # Аватар Леночки
    embed.set_author(
        name="Секретутка Леночка",
        icon_url=SECRETARY_AVATAR
    )

    # Аватар пользователя справа
    embed.set_thumbnail(url=avatar)

    # Discord ID (кликабельный)
    embed.add_field(
        name="Discord ID",
        value=mention,
        inline=False
    )

    # Поля формы
    for f in fields:
        embed.add_field(
            name=f.get("name", "—"),
            value=f.get("value", "—"),
            inline=False
        )

    # Подпись снизу
    embed.set_footer(text="Проверяющие: используйте кнопки ниже для решения заявки 💌")

    # ================= СОЗДАНИЕ ТРЕДА =================
    channel = bot.get_channel(FORUM_CHANNEL_ID)

    thread_data = await channel.create_thread(
        name=f"Заявка — {author_name}",
        content="Новая заявка",
        embed=embed
    )

    thread = thread_data.thread

    # ================= ПИНГ =================
    await thread.send(
        f"{mention} <@924956705756971028> <@695943956856307744> новая заявка!"
    )

    # ================= КНОПКИ =================
    await thread.send(
        "Леночка ждёт решения~ 💌\n\nВыберите действие:",
        view=КнопкиЗаявки(discord_id)
    )

    # ================= РОЛЬ =================
    role = guild.get_role(РОЛЬ_НА_ПРОВЕРКЕ)
    if role and member:
        await member.add_roles(role)

    # ================= ЛС =================
    try:
        await member.send(random.choice(РОФЛ_ПОЛУЧЕНО))
    except:
        pass
# ================= READY =================
@bot.event
async def on_ready():
    print("Леночка запущена")

# ================= FLASK =================
def run():
    app.run("0.0.0.0", port=10000)

threading.Thread(target=run).start()

bot.run(TOKEN)
