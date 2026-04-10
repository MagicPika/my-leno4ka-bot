import discord
from discord.ext import commands
import os, random, asyncio, threading
from flask import Flask, request, jsonify

# ================= НАСТРОЙКИ =================
TOKEN = os.getenv("DISCORD_TOKEN")
SECRET = "2122428Matros"  # НЕ ТРОГАЕМ

FORUM_CHANNEL_ID = 1458885875692732438
LOG_CHANNEL_ID = 1457319047157911565  # поставь свой

РОЛЬ_НА_ПРОВЕРКЕ = 1474320899598581791
РОЛЬ_ОДОБРЕНО = 1457319043315929267

# ================= РОФЛЫ =================
РОФЛ_ПОЛУЧЕНО = [
    "Ооо, свеженькая заявОчка прилетела~ 💌",
    "Леночка уже понесла боссам 💕"
]

РОФЛ_ОДОБРЕНО = [
    "Урааа~ 💕 Боссы сказали ДА!"
]

РОФЛ_ОТКЛОНЕНО = [
    "Ой-ой… отказ 😔"
]

РОФЛ_УТОЧНИТЬ = [
    "Нужно больше информации 📞"
]

# ================= BOT =================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= FLASK =================
app = Flask(__name__)

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
    return jsonify({"ok": True})

# ================= КНОПКИ =================
class Кнопки(discord.ui.View):
    def __init__(self, user, thread, message):
        super().__init__(timeout=None)
        self.user = user
        self.thread = thread
        self.message = message

    async def check(self, interaction):
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("❌ Нет прав", ephemeral=True)
            return False
        return True

    async def finish(self, interaction, text, color):
        # отключаем кнопки
        for i in self.children:
            i.disabled = True

        await interaction.message.edit(view=self)

        # редактируем ОРИГИНАЛЬНЫЙ embed
        embed = self.message.embeds[0]
        embed.title = "Заявка рассмотрена"
        embed.description = text
        embed.color = color
        embed.set_footer(text=f"Решил: {interaction.user}")

        await self.message.edit(embed=embed)

        # лог
        log = interaction.guild.get_channel(LOG_CHANNEL_ID)
        if log:
            await log.send(f"{interaction.user.mention} → {text}")

        # закрываем тред
        await asyncio.sleep(2)
        await self.thread.edit(archived=True, locked=True)

    @discord.ui.button(label="✅ Одобрить", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button):
        if not await self.check(interaction):
            return

        member = interaction.guild.get_member(self.user.id)

        if member:
            role = interaction.guild.get_role(РОЛЬ_ОДОБРЕНО)
            if role:
                await member.add_roles(role)

            try:
                await member.send(random.choice(РОФЛ_ОДОБРЕНО))
            except:
                pass

        await interaction.response.defer()
        await self.finish(interaction, f"✅ {self.user.mention} одобрен", 0x2ecc71)

    @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button):
        if not await self.check(interaction):
            return

        try:
            await self.user.send(random.choice(РОФЛ_ОТКЛОНЕНО))
        except:
            pass

        await interaction.response.defer()
        await self.finish(interaction, f"❌ {self.user.mention} отклонён", 0xe74c3c)

    @discord.ui.button(label="📞 Уточнить", style=discord.ButtonStyle.secondary)
    async def clarify(self, interaction: discord.Interaction, button):
        if not await self.check(interaction):
            return

        try:
            await self.user.send(random.choice(РОФЛ_УТОЧНИТЬ))
        except:
            pass

        await interaction.response.defer()
        await self.finish(interaction, f"📞 {self.user.mention} требуется уточнение", 0xf1c40f)

# ================= ОБРАБОТКА =================
async def обработать_заявку(discord_id, author_name, fields):
    channel = bot.get_channel(FORUM_CHANNEL_ID)
    if not channel:
        return

    thread_data = await channel.create_thread(
        name=f"Заявка — {author_name}",
        content="📋 Новая заявка",
        auto_archive_duration=10080
    )

    thread = thread_data.thread
    guild = thread.guild

    # проверка на сервер
    try:
        member = await guild.fetch_member(discord_id)
    except:
        member = None

    if member is None:
        await thread.send(f"❌ <@{discord_id}> не найден на сервере — отказ")

        try:
            user = await bot.fetch_user(discord_id)
            await user.send("❌ Вы не на сервере — заявка отклонена")
        except:
            pass

        await asyncio.sleep(2)
        await thread.edit(archived=True, locked=True)
        return

    user = await bot.fetch_user(discord_id)

    # embed
    embed = discord.Embed(
        title=f"Заявка от {author_name}",
        color=0x85144b
    )

    embed.add_field(name="Заявитель", value=f"<@{discord_id}>", inline=False)

    for f in fields:
        embed.add_field(name=f.get("name"), value=f.get("value"), inline=False)

    msg = await thread.send(embed=embed)

    await thread.send(f"<@{discord_id}> новая заявка 💌")

    # кнопки (с передачей msg)
    await thread.send("Выберите действие:", view=Кнопки(user, thread, msg))

    # роль
    role = guild.get_role(РОЛЬ_НА_ПРОВЕРКЕ)
    if role:
        await member.add_roles(role)

    # ЛС
    try:
        await user.send(random.choice(РОФЛ_ПОЛУЧЕНО))
    except:
        pass

# ================= RUN =================
def run_flask():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run_flask).start()

bot.run(TOKEN)
