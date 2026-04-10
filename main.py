import discord
from discord.ext import commands
import asyncio
import random
import os
from flask import Flask
import threading

app = Flask(__name__)

TOKEN = os.getenv("DISCORD_TOKEN")

РОЛЬ_НА_ПРОВЕРКЕ = 1474320899598581791
РОЛЬ_ОДОБРЕНО = 1457319043315929267

# ================= РОФЛЫ =================
РОФЛ_ПОЛУЧЕНО = [
    "Ой~ новая заявочка 💕 Леночка уже понесла боссам~",
    "Ммм… интересненько, Леночка читает ☕"
]

РОФЛ_ОДОБРЕНО = [
    "Ура~ 💕 Боссы сказали да!",
    "Добро пожаловать~ Леночка рада ✨"
]

РОФЛ_ОТКЛОНЕНО = [
    "Ой… отказ 😔 Но не расстраивайся",
    "Не в этот раз 💔"
]

РОФЛ_УТОЧНИТЬ = [
    "Нужно чуть больше информации 💕",
    "Расскажи подробнее ✨"
]

# ================= BOT =================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= КНОПКИ =================
class КнопкиЗаявки(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.done = False

    async def finish(self, interaction, text):
        if self.done:
            return
        self.done = True

        member = interaction.guild.get_member(self.user_id)

        # отключаем кнопки
        for item in self.children:
            item.disabled = True

        await interaction.message.edit(view=self)

        # сообщение
        await interaction.channel.send(text)

        # закрываем тред
        await asyncio.sleep(2)
        try:
            await interaction.channel.edit(archived=True, locked=True)
        except:
            pass

    @discord.ui.button(label="✅ Одобрить", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.guild.get_member(self.user_id)

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

        await interaction.response.defer()
        await self.finish(interaction, f"✅ <@{self.user_id}> одобрен")

    @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.guild.get_member(self.user_id)

        if member:
            try:
                await member.send(random.choice(РОФЛ_ОТКЛОНЕНО))
            except:
                pass

        await interaction.response.defer()
        await self.finish(interaction, f"❌ <@{self.user_id}> отклонён")

    @discord.ui.button(label="📞 Уточнить", style=discord.ButtonStyle.secondary)
    async def clarify(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.guild.get_member(self.user_id)

        if member:
            try:
                await member.send(random.choice(РОФЛ_УТОЧНИТЬ))
            except:
                pass

        await interaction.response.defer()
        await self.finish(interaction, f"📞 <@{self.user_id}> требуется уточнение")

# ================= ЛОВИМ WEBHOOK =================
@bot.event
async def on_thread_create(thread):
    await asyncio.sleep(2)

    try:
        starter = await thread.parent.fetch_message(thread.id)
    except:
        return

    if not starter.embeds:
        return

    embed = starter.embeds[0]

    discord_id = None

    for field in embed.fields:
        if field.name == "Discord ID":
            discord_id = field.value.replace("<@", "").replace(">", "").strip()
            break

    if not discord_id:
        return

    discord_id = int(discord_id)

    guild = thread.guild

    # ПИНГ
    await thread.send(f"<@{discord_id}> новая заявка 💌")

    # КНОПКИ
    await thread.send(
        "Выберите действие:",
        view=КнопкиЗаявки(discord_id)
    )

    # РОЛЬ "НА ПРОВЕРКЕ"
    try:
        member = await guild.fetch_member(discord_id)
        role = guild.get_role(РОЛЬ_НА_ПРОВЕРКЕ)
        if role:
            await member.add_roles(role)

        # ЛС
        await member.send(random.choice(РОФЛ_ПОЛУЧЕНО))
    except:
        pass

# ================= READY =================
@bot.event
@app.route("/")
def home():
    return "Леночка работает 💕"

def run():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run).start()
    

bot.run(TOKEN)
