import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

ADMIN_CHANNEL_ID = 1475925864641462445
WELCOME_CHANNEL_ID = 1475912054950072561
pending_verification = {}
welcome_messages = {}
verification_attempts = {}
last_bot_messages = {}
bot_bans = set()

async def change_discord_nick(user_id, nickname):
    guild = bot.get_guild(GUILD_ID)
    if guild:
        member = guild.get_member(user_id)
        if member:
            try:
                await member.edit(nick=nickname)
                print(f"Ник {user_id} изменён на {nickname}")
            except Exception as e:
                print(f"Не удалось сменить ник: {e}")

@bot.event
async def on_ready():
    print(f'Бот {bot.user} успешно запущен и готов к работе!')

@bot.event
async def on_member_join(member):
    welcome_channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if welcome_channel:
        embed = discord.Embed(
            title=f"Добро пожаловать, {member.name}! 🎉",
            description=f"Мы рады приветствовать тебя на сервере Arefulate!\n\n"
                        f"**Пожалуйста, пройди быструю авторизацию, отправив мне личное сообщение (ЛС). Это необходимо для начала общения!**\n\n"
                        f"**После регистрации первым делом проверь канал #пароль для доступа к серверу.**",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        msg = await welcome_channel.send(content=f"||{member.mention}||", embed=embed)
        welcome_messages[member.id] = msg
        if member.id not in verification_attempts:
            verification_attempts[member.id] = 0
    
    try:
        embed = discord.Embed(
            title="Авторизация на сервере",
            description="Привет! Для доступа к серверу, пожалуйста, ответь на несколько вопросов.\n"
                        "**Шаг 1 из 3** - Введи свой **возраст** (только число).",
            color=discord.Color.blue()
        )
        await member.send(embed=embed)
        pending_verification[member.id] = {'stage': 'age', 'data': {}}
    except discord.Forbidden:
        if welcome_channel:
            await welcome_channel.send(f"{member.mention}, не могу отправить тебе личное сообщение. "
                                        f"Пожалуйста, открой ЛС для получения авторизации.")

@bot.event
async def on_member_ban(guild, user):
    if user.id in bot_bans:
        bot_bans.discard(user.id)
        return
    
    try:
        await user.send("Ты был забанен на сервере Arefulate. Чат закрыт.")
    except:
        pass
    
    if user.id in welcome_messages:
        msg = welcome_messages[user.id]
        embed = msg.embeds[0]
        embed.title = f"🚫 Игрок забанен"
        embed.description = ""
        embed.color = discord.Color.dark_red()
        await msg.edit(content=f"||<@{user.id}>||", embed=embed)
        del welcome_messages[user.id]
    
    if user.id in pending_verification:
        del pending_verification[user.id]
    
    if user.id in verification_attempts:
        del verification_attempts[user.id]
    
    if user.id in last_bot_messages:
        del last_bot_messages[user.id]

async def clear_previous_buttons(user):
    if user.id in last_bot_messages:
        try:
            await last_bot_messages[user.id].edit(view=None)
        except:
            pass
        del last_bot_messages[user.id]

async def restart_verification(user):
    await clear_previous_buttons(user)
    verification_attempts[user.id] += 1
    pending_verification[user.id] = {'stage': 'age', 'data': {}}
    embed = discord.Embed(
        title="Авторизация на сервере",
        description="Привет! Для доступа к серверу, пожалуйста, ответь на несколько вопросов.\n"
                    "**Шаг 1 из 3** - Введи свой **возраст** (только число).",
        color=discord.Color.blue()
    )
    await asyncio.sleep(0.5)
    await user.send(embed=embed)

async def update_welcome_message_underage(user_id):
    if user_id in welcome_messages:
        msg = welcome_messages[user_id]
        embed = msg.embeds[0]
        user = bot.get_user(user_id)
        embed.title = f"🚫 Доступ запрещён"
        embed.description = f"Сервер Arefulate доступен только для игроков старше 13 лет."
        embed.color = discord.Color.dark_red()
        await msg.edit(content=f"||<@{user_id}>||", embed=embed)
        del welcome_messages[user_id]
        if user_id in verification_attempts:
            del verification_attempts[user_id]
            
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    if isinstance(message.channel, discord.DMChannel):
        author_id = message.author.id
        if author_id not in pending_verification:
            await message.channel.send("Для начала авторизации зайди на сервер.")
            return
        
        stage = pending_verification[author_id]['stage']
        user_data = pending_verification[author_id]['data']
        
        if stage == 'age':
            if message.content.isdigit():
                age = int(message.content)
                if age < 13:
                    del pending_verification[author_id]
                    await message.channel.send("К сожалению, на сервер допускаются только игроки старше 13 лет. Регистрация закрыта.")
                    try:
                        await update_welcome_message_underage(author_id)
                        guild = bot.guilds[0]
                        member = guild.get_member(author_id)
                        if member:
                            await member.kick(reason="Возраст меньше 13 лет.")
                    except:
                        pass
                    return
                user_data['age'] = age
                pending_verification[author_id]['stage'] = 'nickname'
                await asyncio.sleep(0.5)
                await message.channel.send("Отлично! Теперь введи свой **игровой никнейм**. **(Шаг 2 из 3)**")
            else:
                await asyncio.sleep(0.5)
                await message.channel.send("Пожалуйста, введи возраст числом (например, 18).")
        
        elif stage == 'nickname':
            user_data['nickname'] = message.content
            pending_verification[author_id]['stage'] = 'about'
            await asyncio.sleep(0.5)
            await message.channel.send("Расскажи немного о себе и о том, что планируешь делать на сервере (минимум 20 слов, максимум 100). **(Шаг 3 из 3)**")
        
        elif stage == 'about':
            word_count = len(message.content.split())
            if word_count < 20:
                await asyncio.sleep(0.5)
                await message.channel.send(f"Слишком коротко. Ты написал всего {word_count} слов. Нужно минимум 20. Попробуй ещё раз.")
            elif word_count > 100:
                await asyncio.sleep(0.5)
                await message.channel.send(f"Слишком длинно. Ты написал {word_count} слов. Нужно не больше 100. Сократи и отправь снова.")
            else:
                user_data['about'] = message.content
                await send_verification_to_admin(message.author, user_data)
                del pending_verification[author_id]
                await asyncio.sleep(0.5)
                await message.channel.send("Спасибо! Твои данные отправлены администратору. Ожидай подтверждения.")
        
        return
    
    await bot.process_commands(message)

async def update_welcome_message(user_id, status, user_data=None):
    if user_id in welcome_messages:
        msg = welcome_messages[user_id]
        embed = msg.embeds[0]
        
        if status == "approved":
            user = bot.get_user(user_id)
            embed.title = f"Добро пожаловать, {user.name if user else 'игрок'}! 🎉"
            embed.description = f"Мы рады приветствовать тебя на сервере Arefulate!\n\n**Первым делом проверь канал #пароль для доступа к серверу.**\n\n**✅ Заявка одобрена**"
            embed.color = discord.Color.green()
            await msg.edit(content=f"||<@{user_id}>||", embed=embed)
            del welcome_messages[user_id]
            if user_id in verification_attempts:
                del verification_attempts[user_id]
            if user_data and 'nickname' in user_data:
                await change_discord_nick(user_id, user_data['nickname'])
        elif status == "rejected":
            embed.title = f"❌ Заявка отклонена, {bot.get_user(user_id).name if bot.get_user(user_id) else 'игрок'}"
            embed.description = "**Ты можешь пройти регистрацию снова, для этого ответь боту.**"
            embed.color = discord.Color.red()
            await msg.edit(content=f"||<@{user_id}>||", embed=embed)
        elif status == "kicked":
            embed.title = f"❌ Заявка отклонена, {bot.get_user(user_id).name if bot.get_user(user_id) else 'игрок'}"
            embed.description = ""
            embed.color = discord.Color.red()
            await msg.edit(content=f"||<@{user_id}>||", embed=embed)
            del welcome_messages[user_id]
        elif status == "banned":
            embed.title = f"🚫 Игрок забанен"
            embed.description = ""
            embed.color = discord.Color.dark_red()
            await msg.edit(content=f"||<@{user_id}>||", embed=embed)
            del welcome_messages[user_id]
            if user_id in verification_attempts:
                del verification_attempts[user_id]

async def send_verification_to_admin(user, user_data):
    admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
    if not admin_channel:
        print(f"Ошибка: Канал с ID {ADMIN_CHANNEL_ID} не найден!")
        return
    
    current_attempt = verification_attempts.get(user.id, 0) + 1
    
    embed = discord.Embed(
        title="🔔 Новая заявка на авторизацию",
        color=discord.Color.orange(),
        timestamp=discord.utils.utcnow()
    )
    embed.set_author(name=str(user), icon_url=user.display_avatar.url)
    embed.add_field(name="Пользователь", value=user.mention, inline=True)
    embed.add_field(name="ID пользователя", value=user.id, inline=True)
    embed.add_field(name="Возраст", value=user_data['age'], inline=True)
    embed.add_field(name="Игровой никнейм", value=user_data['nickname'], inline=False)
    embed.add_field(name="О себе", value=user_data['about'][:1024], inline=False)
    embed.add_field(name="Попытка", value=f"{current_attempt}/3", inline=True)

    view = discord.ui.View(timeout=None)
    approve_button = discord.ui.Button(label="✅ Одобрить", style=discord.ButtonStyle.success, custom_id=f"approve_{user.id}")
    reject_button = discord.ui.Button(label="❌ Отклонить", style=discord.ButtonStyle.danger, custom_id=f"reject_{user.id}")
    ban_button = discord.ui.Button(label="⛔ Отказать и забанить", style=discord.ButtonStyle.danger, custom_id=f"ban_{user.id}")

    async def button_callback(interaction):
        allowed_roles = [1475797819733311590, 1476590912875532370, 1475797791358976011, 1475797158828441671]
        if not any(role.id in allowed_roles for role in interaction.user.roles) and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Недостаточно прав.", ephemeral=True)
            return
        
        member = interaction.guild.get_member(user.id)
        if not member:
            await interaction.response.send_message("Пользователь не найден.", ephemeral=True)
            return
        
        if interaction.data['custom_id'].startswith("approve"):
            role = discord.utils.get(interaction.guild.roles, name="Игрок")
            if role:
                try:
                    await member.add_roles(role)
                    await update_welcome_message(user.id, "approved", user_data)
                    
                    embed = discord.Embed(
                        title="✅ Заявка одобрена",
                        color=discord.Color.green(),
                        timestamp=discord.utils.utcnow()
                    )
                    embed.add_field(name="Пользователь", value=f"{member.mention} ({str(member)})", inline=False)
                    embed.add_field(name="Discord ID", value=member.id, inline=True)
                    embed.add_field(name="Возраст", value=user_data['age'], inline=True)
                    embed.add_field(name="Игровой никнейм", value=f"**{user_data['nickname']}**", inline=False)
                    embed.add_field(name="О себе", value=user_data['about'][:1024], inline=False)
                    embed.set_footer(text=f"Одобрено администратором {interaction.user.name}")
                    embed.set_thumbnail(url=member.display_avatar.url)
                    
                    await interaction.response.edit_message(embed=embed, view=None)
                    try:
                        await asyncio.sleep(0.5)
                        await user.send("Поздравляю! Твоя заявка одобрена. Добро пожаловать на сервер!")
                    except:
                        pass
                except discord.Forbidden:
                    await interaction.response.send_message("Нет прав на выдачу роли.", ephemeral=True)
            else:
                await interaction.response.send_message("Роль 'Игрок' не найдена.", ephemeral=True)
        
        elif interaction.data['custom_id'].startswith("reject"):
            if verification_attempts.get(user.id, 0) >= 2:
                await update_welcome_message(user.id, "banned")
                try:
                    await asyncio.sleep(0.5)
                    await user.send("Ты исчерпал все попытки регистрации. Ты был забанен на сервере Arefulate.")
                except:
                    pass
                try:
                    bot_bans.add(user.id)
                    await member.ban(reason="Исчерпаны попытки регистрации.")
                except:
                    pass
                
                embed = discord.Embed(
                    title="🚫 Заявка отклонена - игрок забанен",
                    color=discord.Color.dark_red(),
                    timestamp=discord.utils.utcnow()
                )
                embed.add_field(name="Пользователь", value=f"{member.mention} ({str(member)})", inline=False)
                embed.add_field(name="Discord ID", value=member.id, inline=True)
                embed.add_field(name="Возраст", value=user_data['age'], inline=True)
                embed.add_field(name="Игровой никнейм", value=f"**{user_data['nickname']}**", inline=False)
                embed.add_field(name="О себе", value=user_data['about'][:1024], inline=False)
                embed.add_field(name="Статус", value="Забанен (исчерпаны попытки)", inline=False)
                embed.set_footer(text=f"Отклонено администратором {interaction.user.name}")
                embed.set_thumbnail(url=member.display_avatar.url)
                
                await interaction.response.edit_message(embed=embed, view=None)
                return
            
            await update_welcome_message(user.id, "rejected")
            
            embed = discord.Embed(
                title="❌ Заявка отклонена",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="Пользователь", value=f"{member.mention} ({str(member)})", inline=False)
            embed.add_field(name="Discord ID", value=member.id, inline=True)
            embed.add_field(name="Возраст", value=user_data['age'], inline=True)
            embed.add_field(name="Игровой никнейм", value=f"**{user_data['nickname']}**", inline=False)
            embed.add_field(name="О себе", value=user_data['about'][:1024], inline=False)
            embed.set_footer(text=f"Отклонено администратором {interaction.user.name}")
            embed.set_thumbnail(url=member.display_avatar.url)
            
            await interaction.response.edit_message(embed=embed, view=None)
            
            try:
                retry_view = discord.ui.View(timeout=300)
                retry_button = discord.ui.Button(label="🔄 Попробовать снова", style=discord.ButtonStyle.primary)
                quit_button = discord.ui.Button(label="🚪 Закончить общение", style=discord.ButtonStyle.secondary)
                
                async def retry_callback(retry_interaction):
                    await clear_previous_buttons(user)
                    await retry_interaction.response.edit_message(content=f"Начинаем регистрацию заново, {user.mention}...", view=None)
                    await restart_verification(user)
                
                async def quit_callback(quit_interaction):
                    await update_welcome_message(user.id, "kicked")
                    await quit_interaction.response.edit_message(content="До свидания! Если передумаешь, ты всегда можешь вернуться на сервер.", view=None)
                    try:
                        member = interaction.guild.get_member(user.id)
                        if member:
                            await member.kick(reason="Пользователь завершил общение.")
                    except:
                        pass
                
                retry_button.callback = retry_callback
                quit_button.callback = quit_callback
                
                retry_view.add_item(retry_button)
                retry_view.add_item(quit_button)
                
                await asyncio.sleep(0.5)
                msg = await user.send(f"{user.mention}, к сожалению, твоя заявка была отклонена. Ты можешь попробовать снова или закончить общение.", view=retry_view)
                last_bot_messages[user.id] = msg
            except:
                pass
        
        elif interaction.data['custom_id'].startswith("ban"):
            await update_welcome_message(user.id, "banned")
            
            try:
                await asyncio.sleep(0.5)
                await user.send("Ты был забанен на сервере Arefulate.")
            except:
                pass
            
            try:
                bot_bans.add(user.id)
                await member.ban(reason=f"Заявка отклонена администратором {interaction.user.name}")
            except discord.Forbidden:
                await interaction.response.send_message("Нет прав на бан.", ephemeral=True)
                return
            except discord.NotFound:
                await interaction.response.send_message("Пользователь уже покинул сервер.", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="⛔ Заявка отклонена",
                color=discord.Color.dark_red(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="Пользователь", value=f"{member.mention} ({str(member)})", inline=False)
            embed.add_field(name="Discord ID", value=member.id, inline=True)
            embed.add_field(name="Возраст", value=user_data['age'], inline=True)
            embed.add_field(name="Игровой никнейм", value=f"**{user_data['nickname']}**", inline=False)
            embed.add_field(name="О себе", value=user_data['about'][:1024], inline=False)
            embed.add_field(name="Статус", value="Забанен", inline=False)
            embed.set_footer(text=f"Забанен администратором {interaction.user.name}")
            embed.set_thumbnail(url=member.display_avatar.url)
            
            await interaction.response.edit_message(embed=embed, view=None)

    approve_button.callback = button_callback
    reject_button.callback = button_callback
    ban_button.callback = button_callback
    
    view.add_item(approve_button)
    view.add_item(reject_button)
    view.add_item(ban_button)
    
    await admin_channel.send(embed=embed, view=view)

bot.run(BOT_TOKEN)