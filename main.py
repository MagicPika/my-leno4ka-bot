import discord
from discord.ext import commands
import os, random, asyncio, threading
from flask import Flask, request, jsonify

# ================= НАСТРОЙКИ =================
TOKEN = os.getenv("DISCORD_TOKEN")
SECRET = "2122428Matros"

FORUM_CHANNEL_ID = 1458885875692732438
LOG_CHANNEL_ID = 1286768393478733887  # поменяй

РОЛЬ_НА_ПРОВЕРКЕ = 1474320899598581791
РОЛЬ_ОДОБРЕНО = 1457319043315929267

active_applications = set()

# ================= РОФЛЫ =================
РОФЛ_ПОЛУЧЕНО = ["Леночка получила заявку 💌"]
РОФЛ_ОДОБРЕНО = ["Одобрено 💕"]
РОФЛ_ОТКЛОНЕНО = ["Отказ 😔"]
РОФЛ_УТОЧНИТЬ = ["Нужно уточнение 📞"]

# ================= BOT =================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= FLASK =================
app = Flask(__name__)

@app.route("/zayavka", methods=["POST"])
def принимать_заявку():
    if request.headers.get("Authorization") != f"Bearer {SECRET}":
        return jsonify({"error": "bad key"}), 401

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
        self.ответственный = None

    def check_owner(self, interaction):
        return self.ответственный is None or interaction.user.id == self.ответственный

    async def check(self, interaction):
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("❌ Нет прав", ephemeral=True)
            return False
        if not self.check_owner(interaction):
            await interaction.response.send_message("❌ Уже занято", ephemeral=True)
            return False
        return True

    async def update_status(self, статус, кто=None):
        embed = self.message.embeds[0]
        embed.set_field_at(0, name="Статус", value=статус, inline=False)
        if кто:
            embed.set_footer(text=f"Ответственный: {кто}")
        await self.message.edit(embed=embed)

    async def finish(self, interaction, текст, цвет):
        for i in self.children:
            i.disabled = True

        await interaction.message.edit(view=self)

        embed = self.message.embeds[0]
        embed.title = "Заявка рассмотрена"
        embed.description = текст
        embed.color = цвет
        embed.set_footer(text=f"Решил: {interaction.user}")

        await self.message.edit(embed=embed)

        try:
            if "одобрен" in текст:
                await self.thread.edit(name=f"✅ Одобрено — {self.user.name}")
            elif "отклонён" in текст:
                await self.thread.edit(name=f"❌ Отказ — {self.user.name}")
            elif "уточнение" in текст:
                await self.thread.edit(name=f"📞 Уточнение — {self.user.name}")
        except:
            pass

        active_applications.discard(self.user.id)

        await asyncio.sleep(2)
        await self.thread.edit(archived=True, locked=True)

    @discord.ui.button(label="👤 Взять", style=discord.ButtonStyle.primary)
    async def take(self, interaction: discord.Interaction, button):
        if not await self.check(interaction):
            return
        self.ответственный = interaction.user.id
        await interaction.response.send_message("Взял заявку", ephemeral=True)
        await self.update_status("🟡 В работе", interaction.user)

    @discord.ui.button(label="🔁 Передать", style=discord.ButtonStyle.secondary)
    async def transfer(self, interaction: discord.Interaction, button):
        if self.ответственный != interaction.user.id:
            await interaction.response.send_message("❌ Не ты ответственный", ephemeral=True)
            return
        self.ответственный = None
        await interaction.response.send_message("Передано", ephemeral=True)
        await self.update_status("🟣 Ожидает")

    @discord.ui.button(label="✅", style=discord.ButtonStyle.success)
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

    @discord.ui.button(label="❌", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button):
        if not await self.check(interaction):
            return
        try:
            await self.user.send(random.choice(РОФЛ_ОТКЛОНЕНО))
        except:
            pass
        await interaction.response.defer()
        await self.finish(interaction, f"❌ {self.user.mention} отклонён", 0xe74c3c)

    @discord.ui.button(label="📞", style=discord.ButtonStyle.secondary)
    async def clarify(self, interaction: discord.Interaction, button):
        if not await self.check(interaction):
            return
        try:
            await self.user.send(random.choice(РОФЛ_УТОЧНИТЬ))
        except:
            pass
        await interaction.response.defer()
        await self.finish(interaction, f"📞 {self.user.mention} уточнение", 0xf1c40f)

# ================= ОБРАБОТКА =================
async def обработать_заявку(discord_id, author_name, fields):

    if discord_id in active_applications:
        return
    active_applications.add(discord_id)

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

    try:
        member = await guild.fetch_member(discord_id)
    except:
        member = None

    if member is None:
        await thread.send(f"❌ <@{discord_id}> не на сервере")
        await asyncio.sleep(2)
        await thread.edit(archived=True, locked=True)
        active_applications.discard(discord_id)
        return

    user = await bot.fetch_user(discord_id)

    avatar = user.avatar.url if user.avatar else user.default_avatar.url

    embed = discord.Embed(
        title=f"Заявка от {author_name}",
        color=0x85144b,
        timestamp=discord.utils.utcnow()
    )

    embed.set_thumbnail(url=avatar)
    embed.add_field(name="Статус", value="🟣 Ожидает", inline=False)
    embed.add_field(name="Заявитель", value=f"<@{discord_id}>", inline=False)

    for f in fields:
        embed.add_field(name=f.get("name"), value=f.get("value"), inline=False)

    msg = await thread.send(embed=embed)

    await thread.send("Выберите действие:", view=Кнопки(user, thread, msg))

    role = guild.get_role(РОЛЬ_НА_ПРОВЕРКЕ)
    if role:
        await member.add_roles(role)

    try:
        await user.send(random.choice(РОФЛ_ПОЛУЧЕНО))
    except:
        pass

# ================= RUN =================
def run_flask():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run_flask).start()

bot.run(TOKEN)
