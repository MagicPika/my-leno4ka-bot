# main.py
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Modal, TextInput, View
import os, random, sys, asyncio, threading
from flask import Flask, request, jsonify

app = Flask(__name__)

# === НАСТРОЙКИ ===
TOKEN = os.getenv("DISCORD_TOKEN")
FORUM_CHANNEL_ID = 1458885875692732438
SECRET = "2122428Matros"

РОЛЬ_НА_ПРОВЕРКЕ = 1474320899598581791
РОЛЬ_ОДОБРЕНО = 1457319043315929267

# ------------------ РОФЛЫ ------------------
РОФЛ_ПОЛУЧЕНО = [
    "Ооо, свеженькая заявОчка прилетела~ Леночка уже несёт боссам! 💌",
    "Привет! Леночка увидела твою анкету 💓 Сейчас покажу наверх~"
]
РОФЛ_ОДОБРЕНО = [
    "Урааа~ 💕 Боссы сказали ДА! Заходи скорее!",
    "Одобрено! Леночка в восторге, ты с нами навсегда 😘✨"
]
РОФЛ_ОТКЛОНЕНО = [
    "Ой-ой… боссы сказали нет 😔 Но не грусти, Леночка обнимает 💔",
    "К сожалению, отказ… Но ты всё равно классный 😌"
]
РОФЛ_УТОЧНИТЬ = [
    "Боссы хотят уточнить детали! Напиши сюда, я передам 📞💕",
    "Нужно больше инфы… Пиши в ЛС Леночке 🖊️"
]

# ================= Flask для формы =================
@app.route("/zayavka", methods=["POST"])
def принимать_заявку():
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {SECRET}":
        return jsonify({"error": "Неверный ключ"}), 401
    data = request.json or {}
    discord_id = data.get("discordId")
    author_name = data.get("authorName", "Без имени")
    fields = data.get("fields", [])

    if not discord_id or not str(discord_id).isdigit():
        return jsonify({"error": "Нет нормального discordId"}), 400

    bot.loop.create_task(обработать_заявку_2_0(int(discord_id), author_name, fields))
    return jsonify({"status": "ok"}), 200

# ================= Обработка заявки =================
async def обработать_заявку_2_0(discord_id: int, author_name: str, fields: list):
    try:
        user = await bot.fetch_user(discord_id)
        avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
    except:
        avatar_url = f"https://cdn.discordapp.com/embed/avatars/{discord_id % 6}.png"

    embed = discord.Embed(
        title=f"Заявка от {author_name}",
        description="Ожидает решения боссов",
        color=0x85144b,
        timestamp=discord.utils.utcnow()
    )
    embed.set_thumbnail(url=avatar_url)

    clean_id = str(discord_id)
    embed.add_field(name="Discord ID", value=f"<@{clean_id}>", inline=False)
    for f in fields:
        embed.add_field(name=f.get("name","—"), value=f.get("value","—"), inline=f.get("inline", False))
    embed.set_footer(text="Проверяющие: используйте кнопки ниже для решения заявки 💌")

    # Форумный канал
    channel = bot.get_channel(FORUM_CHANNEL_ID)
    if not channel:
        print("Форумный канал не найден")
        return

    try:
        # Создаём тред с embed
        thread_with_msg = await channel.create_thread(
            name=f"Заявка — {author_name}",
            embed=embed,
            auto_archive_duration=10080
        )

        thread = thread_with_msg.thread
        msg = thread_with_msg.message

        # Пинг боссов
        ping = f"<@924956705756971028> <@695943956856307744> <@&1457319043672576008>"
        await thread.send(ping + " новая заявка! Леночка ждёт решения~ 💌")

        # ================= Кнопки =================
class КнопкиЗаявки(View):
    def __init__(self, user: discord.User, thread: discord.Thread):
        super().__init__(timeout=None)
        self.user = user
        self.thread = thread  # ← передаём thread в класс

    @discord.ui.button(label="✅ Одобрить", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = guild.get_member(self.user.id)
        if member:
            role_check = guild.get_role(РОЛЬ_НА_ПРОВЕРКЕ)
            if role_check in member.roles:
                await member.remove_roles(role_check)
            role_ok = guild.get_role(РОЛЬ_ОДОБРЕНО)
            if role_ok:
                await member.add_roles(role_ok)
        await self.user.send(random.choice(РОФЛ_ОДОБРЕНО))
        await interaction.response.send_message(f"Заявка {self.user.mention} одобрена ✅", ephemeral=True)
        
        # Добавляем тег "Одобрена" (если канал форумный)
        try:
            теги = self.thread.available_tags
            одобрена_тег = next((t for t in теги if t.name == "Одобрена"), None)
            if одобрена_тег:
                await self.thread.add_tags([одобрена_тег])
        except:
            pass  # если не форум — просто пропускаем
        
        self.stop()

    @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.user.send(random.choice(РОФЛ_ОТКЛОНЕНО))
        await interaction.response.send_message(f"Заявка {self.user.mention} отклонена ❌", ephemeral=True)
        
        try:
            теги = self.thread.available_tags
            отклонена_тег = next((t for t in теги if t.name == "Отклонена"), None)
            if отклонена_тег:
                await self.thread.add_tags([отклонена_тег])
        except:
            pass
        
        self.stop()

    @discord.ui.button(label="📞 Уточнить", style=discord.ButtonStyle.secondary)
    async def clarify(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.user.send(random.choice(РОФЛ_УТОЧНИТЬ))
        await interaction.response.send_message(f"Попросили уточнения у {self.user.mention} 📞", ephemeral=True)
        
        try:
            теги = self.thread.available_tags
            уточнение_тег = next((t for t in теги if t.name == "На уточнении"), None)
            if уточнение_тег:
                await self.thread.add_tags([уточнение_тег])
        except:
            pass
        
        self.stop()

        view = КнопкиЗаявки(user=user, thread=thread)
        await thread.send("Выберите действие:", view=view)

    except Exception as e:
        print(f"Ошибка создания треда или кнопок: {e}")
        return

    # Роль "На проверке"
    try:
        guild = bot.get_guild(thread.guild.id)
        if guild:
            member = await guild.fetch_member(discord_id)
            if member:
                роль_проверка = guild.get_role(РОЛЬ_НА_ПРОВЕРКЕ)
                if роль_проверка:
                    await member.add_roles(роль_проверка, reason="Новая заявка — на проверке")
    except Exception as e:
        print(f"Ошибка выдачи роли 'На проверке': {e}")

    # ЛС заявителю
    try:
        await user.send(random.choice(РОФЛ_ПОЛУЧЕНО))
    except:
        pass

    # Таймер напоминания
    async def таймер_леночки():
        await asyncio.sleep(24*3600)
        try:
            await thread.send("Боссики, прошло 24 часа, Леночка напоминает о заявке 😌")
        except:
            pass
    bot.loop.create_task(таймер_леночки())


# ================= Бот =================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Леночка готова → {bot.user}")
    await bot.tree.sync()
    print("Слэш-команды синхронизированы")

# ================= Статус заявок =================
@bot.command(name="статус")
async def статус_заявок(ctx):
    канал = bot.get_channel(FORUM_CHANNEL_ID)
    if not канал or канал.type != discord.ChannelType.forum:
        await ctx.send("Форумный канал не найден 😔")
        return
    треды = [t async for t in канал.threads() if not t.archived]
    ответ = f"Всего активных заявок: {len(треды)}"
    await ctx.send(ответ)

# ================= Похвала =================
@bot.command(name="похвали")
async def похвали(ctx, member: discord.Member=None):
    if not member:
        онлайн = [m for m in ctx.guild.members if not m.bot and m.status != discord.Status.offline]
        member = random.choice(онлайн) if онлайн else ctx.author
    await ctx.send(f"{member.mention}, Леночка думает, какой ты молодец! 💖")

# ================= Настройки =================
@bot.tree.command(name="настройки")
@app_commands.default_permissions(administrator=True)
async def слэш_настройки(interaction: discord.Interaction):
    embed = discord.Embed(title="Настройки Леночки", color=0xff69b4)
    embed.add_field(name="Форумный канал", value=f"<#{FORUM_CHANNEL_ID}>", inline=False)
    view = discord.ui.View(timeout=180)
    кнопка = discord.ui.Button(label="Изменить настройки", style=discord.ButtonStyle.primary)
    async def открыть_модалку(intf):
        await intf.response.send_modal(НастройкиМодалка())
    кнопка.callback = открыть_модалку
    view.add_item(кнопка)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class НастройкиМодалка(Modal, title="Изменить настройки Леночки"):
    канал = TextInput(label="Новый форум", placeholder="#канал или ID", required=False)
    роль_одобрено = TextInput(label="Роль 'Одобрено'", placeholder="@Роль или ID", required=False)
    async def on_submit(self, interaction: discord.Interaction):
        global FORUM_CHANNEL_ID, РОЛЬ_ОДОБРЕНО
        if self.канал.value.strip():
            FORUM_CHANNEL_ID = int(self.канал.value.strip("<#> "))
        if self.роль_одобрено.value.strip():
            РОЛЬ_ОДОБРЕНО = int(self.роль_одобрено.value.strip("<@&> "))
        await interaction.response.send_message("Настройки обновлены 💕", ephemeral=True)
# ================= Пересылка ЛС в тред =================
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if isinstance(message.channel, discord.DMChannel):
        user_id = message.author.id
        for guild in bot.guilds:
            forum = guild.get_channel(FORUM_CHANNEL_ID)
            if forum and hasattr(forum, "threads"):
                async for thread in forum.threads:
                    if not thread.archived and thread.name.startswith("Заявка"):
                        try:
                            embed = (await thread.fetch_message(thread.id)).embeds[0]
                            discord_field = next((f for f in embed.fields if f.name=="Discord ID"), None)
                            if discord_field and str(user_id) in discord_field.value:
                                await thread.send(f"📩 Сообщение от {message.author.mention}:\n{message.content}")
                        except:
                            continue
        return


# ================= Flask =================
def run_flask():
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
threading.Thread(target=run_flask, daemon=True).start()

# ================= Запуск =================
bot.run(TOKEN)




