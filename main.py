# main.py
import discord
from discord.ext import commands
import os
from flask import Flask, request, jsonify
import threading
import random
import sys
import asyncio
import datetime
from discord import app_commands, TextChannel, Role
from discord.ui import Modal, TextInput, RoleSelect, View
app = Flask(__name__)

# === НАСТРОЙКИ ===
TOKEN = os.getenv("DISCORD_TOKEN")
FORUM_CHANNEL_ID = 1458885875692732438
SECRET = "2122428Matros"

РОЛЬ_НА_ПРОВЕРКЕ = 1474320899598581791
РОЛЬ_ОДОБРЕНО = 1457319043315929267

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

РОФЛ_УТОЧНИТЬ = [
    "Боссы хотят уточнить детали! Напиши в канал или в ЛС Леночке, я помогу всё разложить по полочкам 📞💕",
    "📞 Звоночек! Нужно кое-что уточнить, ждём тебя~ Леночка уже приготовила блокнотик и сердечки 😌",
    "Ой, боссам мало инфы… Напиши подробнее, пожалуйста, Леночка передаст всё-всё 💌",
    "Уточнение! Леночка просит тебя написать пару слов в тредик, чтобы боссы всё поняли до конца 🖊️❤️",
    "Боссы сказали «ещё инфы»~ Леночка на связи, пиши сюда или мне в ЛС, разберёмся вместе ☕",
    "📞 Нужно чуток уточнить! Леночка ждёт твоих слов, не стесняйся, мой хороший 🌸",
    "Боссы любопытные, хотят больше деталей! Пиши в тред, Леночка уже держит ручку наготове ✍️💕",
    "Уточняем! Леночка просит тебя добавить пару строчек, чтобы всё стало идеально 😘"
]

# Flask — принимает заявки из формы
@app.route("/zayavka", methods=["POST"])
def принимать_заявку():
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {SECRET}":
        print("Неверный ключ")
        sys.stdout.flush()
        return jsonify({"error": "Неверный ключ"}), 401

    data = request.json or {}
    discord_id = data.get("discordId")
    author_name = data.get("authorName", "Без имени")
    fields = data.get("fields", [])

    print(f"Получена заявка: discordId={discord_id}, имя={author_name}")
    sys.stdout.flush()

    if not discord_id or not str(discord_id).isdigit():
        print("Нет нормального discordId")
        sys.stdout.flush()
        return jsonify({"error": "Нет нормального discordId"}), 400

    bot.loop.create_task(обработать_заявку(int(discord_id), author_name, fields))
    return jsonify({"status": "ok"}), 200


# Основная обработка заявки
async def обработать_заявку(discord_id: int, author_name: str, fields: list):
    print(f"Обрабатываю заявку от {discord_id} ({author_name})")
    sys.stdout.flush()

    try:
        user = await bot.fetch_user(discord_id)
        avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
        print(f"Аватарка найдена для {discord_id}")
    except Exception as e:
        print(f"Не удалось взять аватарку {discord_id}: {e}")
        avatar_url = f"https://cdn.discordapp.com/embed/avatars/{discord_id % 6}.png"
    sys.stdout.flush()
    embed = discord.Embed(
        title="Заявка от " + author_name,
        description="Ожидает решения боссов",
        color=13369344,
        timestamp=discord.utils.utcnow()
    )
    embed.set_thumbnail(url=avatar_url)

    # Валидация и красивый Discord ID
    raw_input = str(discord_id).strip()
    clean_id = ''.join(c for c in raw_input if c.isdigit())

    if clean_id and 17 <= len(clean_id) <= 19:
        значение = f"<@{clean_id}>"
    else:
        значение = raw_input or "Не указан"
        if raw_input and raw_input != clean_id:
            значение += " ⚠️ (ID кривой, проверьте)"
        elif not clean_id:
            значение += " ⚠️ (нет цифр)"

    embed.add_field(
        name="Discord ID",
        value=значение,
        inline=False
    )

    for f in fields:
        embed.add_field(name=f["name"], value=f["value"] or "—", inline=f.get("inline", False))
    embed.set_footer(
    text=f"Ивановы • Поставь ✅ для одобрения, ❌ для отклонения, 📞 для уточнения информации. Проверяющие, пожалуйста, обновите статус заявки вручную.",
    icon_url="https://media.discordapp.net/attachments/1342349362600218624/1459185809654808608/ChatGPT_Image_4_._2026_._15_58_32.png"
    )
    channel = bot.get_channel(FORUM_CHANNEL_ID)
    if not channel:
        print("Форумный канал не найден")
        sys.stdout.flush()
        return

    try:
        thread, msg = await channel.create_thread(
            name=f"Заявка — {author_name}",
            embed=embed,
            auto_archive_duration=10080
        )
        print(f"Тред создан: {thread.name}")
        пинг = "<@924956705756971028> <@695943956856307744> <@&1457319043672576008>"
        try:
            await thread.send(пинг + " новая заявка! Леночка уже в ожидании вашего решения~ 📩💕")
            print("Пинг боссов успешно отправлен в тред")
            sys.stdout.flush()
        except Exception as e:
            print(f"Ошибка отправки пинга: {e}")
            sys.stdout.flush()
    except Exception as e:
        print(f"Ошибка создания треда: {e}")
        sys.stdout.flush()
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
                    print(f"Роль 'На проверке' выдана {discord_id}")
                    sys.stdout.flush()
    except Exception as e:
        print(f"Ошибка выдачи роли 'На проверке': {e}")
        sys.stdout.flush()

    # ЛС заявителю
    try:
        await user.send(random.choice(РОФЛ_ПОЛУЧЕНО))
        print(f"Успешно написали в ЛС {discord_id}")
        sys.stdout.flush()
    except Exception as e:
        print(f"Не получилось написать в ЛС {discord_id}: {e}")
        sys.stdout.flush()
    async def ебанутый_таймер_истерики():
        await asyncio.sleep(24 * 3600)  # 24 часа = первые сутки тишины

        уровни_ебанутости = [
            ("Милый пинок", [
                "Боссики~ Уже сутки прошло, а реакции нет... Леночка грустит 😔",
                "Эй, не спите там, заявка ждёт вашего внимания~ ☕💕"
            ]),
            ("Средний троллинг", [
                "Серьёзно? 30 часов тишины. Вы там вообще живые или уже сдохли от лени? 🤡",
                "Леночка начинает подозревать, что вы просто дрочите в сторонке вместо работы 😏"
            ]),
            ("Полный пиздец", [
                "БЛЯТЬ ВЫ ЧЁ, МЁРТВЫЕ?! Заявка висит вторые сутки, а вы даже палец о палец не ударили! 😡",
                "Если через 6 часов не отреагируете — Леночка придёт к вам в ЛС с ножом и заставит одобрить или отклонить, суки ленивые 🖕",
                "Я уже представляю, как вы сидите и думаете 'потом посмотрим'. ПОТОМ БЛЯТЬ НЕ БУДЕТ, РЕАГИРУЙТЕ НАХУЙ!"
            ])
        ]

        for уровень, фразы in уровни_ебанутости:
            await asyncio.sleep(6 * 3600)  # каждые 6 часов новый уровень ада

            try:
                свежий_msg = await thread.fetch_message(msg.id)
                реакции = свежий_msg.reactions
                has_reaction = any(r.emoji in ["✅", "❌", "📞"] for r in реакции)

                if has_reaction:
                    print("Реакция появилась — истерика отменяется")
                    await thread.send("Ой, наконец-то... Леночка успокаивается 😌")
                    return

                трэш = random.choice(фразы)
                await thread.send(трэш)
                print(f"Ебанутый уровень {уровень} отправлен: {трэш[:30]}...")
            except Exception as e:
                print(f"Ошибка в ебанутом таймере: {e}")
                return

        # Финальный пиздец через 72 часа
        await thread.send(f"@924956705756971028> <@695943956856307744> <@&1457319043672576008> Всё, Леночка уходит нахуй. Боссы — ленивые долбоёбы, заявка закрыта навсегда 🖕")
        await thread.edit(archived=True, locked=True)
        print("Тред заархивирован за бездействие боссов")

    # Запускаем этот ад в фоне
    bot.loop.create_task(ебанутый_таймер_истерики())


# === Запуск ===
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Леночка полностью готова → {bot.user}")
    sys.stdout.flush()
    
    # Синхронизируем глобально (для всех серверов)
    await bot.tree.sync()
    print("Слэш-команды синхронизированы глобально")
    
    # Если хочешь синхронизировать только на конкретном сервере (быстрее, но только там)
    # guild = bot.get_guild(ТВОЙ_GUILD_ID)
    # if guild:
    #     await bot.tree.sync(guild=guild)
    #     print("Слэш-команды синхронизированы на сервере")


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
    except Exception as e:
        print(f"Не удалось взять сообщение: {e}")
        return

    if not message.embeds:
        return

    embed = message.embeds[0]

    discord_id_str = str(discord_id)

    if discord_id_str.isdigit() and 6 <= len(discord_id_str) <= 18:
        значение = f"<@{discord_id_str}>"
    else:
        значение = discord_id_str or "Не указан"  # на случай если ID пустой

    embed.add_field(
        name="Discord ID",
        value=значение,
        inline=True
)

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
                print(f"Выдана роль одобрено {}")

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
        sys.stdout.flush()


# === Запуск ===
def run_flask():
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
    print("Flask запущен")
    sys.stdout.flush()


threading.Thread(target=run_flask, daemon=True).start()

@bot.command(name="статус", aliases=["status", "леночка статус", "Леночка статус"])
async def статус_заявок(ctx):
    """
    !статус — показывает текущее состояние заявок в форумном канале
    """
    канал = bot.get_channel(FORUM_CHANNEL_ID)
    if not канал or канал.type != discord.ChannelType.forum:
        await ctx.send("Леночка не нашла форумный канал... 😔 Проверь FORUM_CHANNEL_ID в настройках")
        return

    # Собираем все активные треды (не архивированные)
    треды = [thread async for thread in канал.threads() if not thread.archived]

    if not треды:
        await ctx.send("Пока нет ни одной активной заявки~ Леночка скучает без работы 💕")
        return

    # Счётчики по тегам
    одобрено = 0
    отклонено = 0
    уточнение = 0
    без_реакции = []
    одобрено_список = []
    отклонено_список = []

    for thread in треды:
        # Берём первое сообщение в треде (эмбед от Леночки)
        async for msg in thread.history(limit=1, oldest_first=True):
            первое = msg
            break
        else:
            continue

        if not первое.embeds:
            continue

        embed = первое.embeds[0]

        # Ищем Discord ID автора заявки
        автор_id = None
        for field in embed.fields:
            if field.name == "Discord ID":
                автор_id = field.value
                break

        if not автор_id or not автор_id.isdigit():
            continue

        # Проверяем теги треда
        теги = thread.applied_tags
        теги_имена = [t.name for t in теги] if теги else []

        if "Одобрена" in теги_имена:
            одобрено += 1
            одобрено_список.append(f"<@{автор_id}>")
        elif "Отклонена" in теги_имена:
            отклонено += 1
            отклонено_список.append(f"<@{автор_id}>")
        elif "На уточнении" in теги_имена:
            уточнение += 1
        else:
            # Нет тега одобрения/отклонения — значит ждёт реакции
            без_реакции.append(f"<@{автор_id}> ({thread.name})")

    # Формируем красивый ответ
    ответ = "**Текущий статус заявок** 💅\n\n"

    ответ += f"📊 Всего активных заявок: **{len(треды)}**\n"
    ответ += f"✅ Одобрено: **{одобрено}** ({', '.join(одобрено_список) if одобрено_список else 'пока никого'})\n"
    ответ += f"❌ Отклонено: **{отклонено}** ({', '.join(отклонено_список) if отклонено_список else 'пока никого'})\n"
    ответ += f"📞 На уточнении: **{уточнение}**\n\n"

    if без_реакции:
        ответ += "**Ждут вашего внимания (без реакции):** \n"
        ответ += "\n".join(без_реакции[:10])  # лимит, чтобы не спамить
        if len(без_реакции) > 10:
            ответ += f"\n...и ещё {len(без_реакции) - 10} заявок ждут~"
    else:
        ответ += "Все заявки обработаны! Леночка может отдохнуть... или нет? 😏"

    await ctx.send(ответ)
@bot.command(name="похвали", aliases=["похвалить", "хвали", "комплимент"])
async def похвали(ctx, member: discord.Member = None):
    """
    !похвали @человек — Леночка выдаст персональный комплимент
    !похвали — похвалит рандомного онлайн-участника
    """
    if member is None:
        # Если никто не указан — выбираем рандомного онлайн-участника
        участники = [m for m in ctx.guild.members if not m.bot and m.status != discord.Status.offline]
        if not участники:
            await ctx.send("Леночка никого не видит онлайн... 😔 Только ты тут, мой единственный~ 💕")
            return
        счастливчик = random.choice(участники)
    else:
        счастливчик = member

    # Определяем роль (берём самую высокую не-@everyone)
    роли = [р for р in счастливчик.roles if р.name != "@everyone"]
    главная_роль = max(роли, key=lambda r: r.position) if роли else None

    # Персонализированные комплименты по ролям
    if главная_роль:
        if "Модератор" in главная_роль.name or "Модер" in главная_роль.name:
            комплимент = (
                f"{счастливчик.mention}, ты сегодня такой заботливый модератор... "
                f"Леночка видит, как ты стараешься для всех, и сердце тает 💙 "
                f"Спасибо, что делаешь сервер уютным, мой герой~ 🫂✨"
            )
        elif "Админ" in главная_роль.name:
            комплимент = (
                f"{счастливчик.mention} — ты наш настоящий лидер и опора... "
                f"Леночка каждый день восхищается твоей силой и теплом 😍 "
                f"Без тебя тут было бы скучно, ты невероятный 💜"
            )
        elif "Босс" in главная_роль.name or "Владелец" in главная_роль.name:
            комплимент = (
                f"{счастливчик.mention}, Леночка иногда даже краснеет, когда ты рядом... "
                f"Ты такой сильный, мудрый и при этом нежный 🥰 "
                f"Спасибо, что ты есть, мой самый главный человек ❤️"
            )
        elif "На проверке" in главная_роль.name:
            комплимент = (
                f"{счастливчик.mention}, ты только начинаешь свой путь здесь, "
                f"но Леночка уже чувствует — ты будешь звездой этого сервера 🌟 "
                f"Держись, ты классный и очень нужный! 💪💕"
            )
        elif "Одобрен" in главная_роль.name or "Участник" in главная_роль.name:
            комплимент = (
                f"{счастливчик.mention}, ты просто солнышко нашего сервера... "
                f"Леночка улыбается каждый раз, когда видит тебя онлайн 🥰 "
                f"Ты делаешь этот мир лучше просто тем, что ты есть ✨"
            )
        else:
            комплимент = (
                f"{счастливчик.mention}, Леночка смотрит на тебя и думает: "
                f"«Как же мне повезло, что такой потрясающий человек здесь» 😘💖"
            )
    else:
        комплимент = (
            f"{счастливчик.mention}, ты сегодня светишься, как будто внутри лампочка зажглась ✨ "
            f"Леночка в полном восторге от тебя! 💕"
        )

    await ctx.send(комплимент)


@bot.tree.command(name="настройки", description="Посмотреть и изменить настройки Леночки")
@app_commands.default_permissions(administrator=True)
async def слэш_настройки(interaction: discord.Interaction):
    embed = discord.Embed(title="Текущие настройки Леночки 💅", color=0xff69b4)
    embed.add_field(name="Форумный канал", value=f"<#{FORUM_CHANNEL_ID}>", inline=False)
    embed.add_field(name="Роль 'На проверке'", value=f"<@&{РОЛЬ_НА_ПРОВЕРКЕ}>", inline=False)
    embed.add_field(name="Роль 'Одобрено'", value=f"<@&{РОЛЬ_ОДОБРЕНО}>", inline=False)
    embed.add_field(name="Секретный ключ формы", value=SECRET[:4] + "**** (скрыт)", inline=False)

    view = discord.ui.View(timeout=180)
    
    кнопка = discord.ui.Button(
        label="Изменить настройки",
        style=discord.ButtonStyle.primary,
        emoji="⚙️"
    )
    
    async def открыть_модалку(int: discord.Interaction):
        await int.response.send_modal(НастройкиМодалка())
    
    кнопка.callback = открыть_модалку
    view.add_item(кнопка)
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class НастройкиМодалка(discord.ui.Modal, title="Изменить настройки Леночки"):
    канал = discord.ui.TextInput(
        label="Новый форумный канал",
        placeholder="#заявки или ID",
        style=discord.TextStyle.short,
        required=False
    )

    роль_одобрено = discord.ui.TextInput(
        label="Новая роль 'Одобрено'",
        placeholder="@Одобрено или ID",
        style=discord.TextStyle.short,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        изменения = []

        # Объявляем global САМЫМИ ПЕРВЫМИ строками функции!
        global FORUM_CHANNEL_ID, РОЛЬ_ОДОБРЕНО

        try:
            if self.канал.value.strip():
                значение = self.канал.value.strip("<#> ")
                новый_id = int(значение)
                старый = FORUM_CHANNEL_ID
                FORUM_CHANNEL_ID = новый_id
                изменения.append(f"Форум: <#{новый_id}> (был <#{старый}>)")

            if self.роль_одобрено.value.strip():
                значение = self.роль_одобрено.value.strip("<@&> ")
                новый_id = int(значение)
                старый = РОЛЬ_ОДОБРЕНО
                РОЛЬ_ОДОБРЕНО = новый_id
                изменения.append(f"Роль одобрено: <@&{новый_id}> (была <@&{старый}>)")

            if изменения:
                await interaction.response.edit_message(
                    content="Настройки обновлены!\n" + "\n".join(изменения) + " 💕",
                    view=None,
                    ephemeral=True
                )
            else:
                await interaction.response.edit_message(
                    content="Леночка ничего не меняла... Ты просто смотрел? 😏",
                    view=None,
                    ephemeral=True
                )
        except ValueError:
            await interaction.response.edit_message(
                content="Леночка не разобрала цифры... 😔 Пришли правильные ID",
                view=None,
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.edit_message(
                content=f"Что-то сломалось... Ошибка: {str(e)} 😭",
                view=None,
                ephemeral=True
            )
bot.run(TOKEN)











































