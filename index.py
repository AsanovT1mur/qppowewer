import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

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
                        f"**Отправь мне личное сообщение, чтобы вступить на сервер.**",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        msg = await welcome_channel.send(content=f"||{member.mention}||", embed=embed)
        welcome_messages[member.id] = msg
        if member.id not in verification_attempts:
            verification_attempts[member.id] = 0
    
    try:
        embed = discord.Embed(
            title="Подтверждение личности",
            description="Привет! Ответь на пару вопросов для доступа к серверу.\n"
                        "**Шаг 1 из 3** — Напиши свой **возраст** (только цифры).",
            color=discord.Color.blue()
        )
        await member.send(embed=embed)
        pending_verification[member.id] = {'stage': 'age', 'data': {}}
    except discord.Forbidden:
        if welcome_channel:
            await welcome_channel.send(f"{member.mention}, я не могу написать тебе в ЛС. "
                                        f"Открой личные сообщения.")

@bot.event
async def on_member_ban(guild, user):
    if user.id in bot_bans:
        bot_bans.discard(user.id)
        return
    
    try:
        await user.send("Ты был забанен на сервере Arefulate.")
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
        title="Подтверждение личности",
        description="Привет! Ответь на пару вопросов для доступа к серверу.\n"
                    "**Шаг 1 из 3** — Напиши свой **возраст** (только цифры).",
        color=discord.Color.blue()
    )
    await asyncio.sleep(0.5)
    await user.send(embed=embed)
            
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    if isinstance(message.channel, discord.DMChannel):
        author_id = message.author.id
        if author_id not in pending_verification:
            await message.channel.send("Для начала зайди на сервер.")
            return
        
        stage = pending_verification[author_id]['stage']
        user_data = pending_verification[author_id]['data']
        
        if stage == 'age':
            if message.content.isdigit():
                user_data['age'] = int(message.content)
                pending_verification[author_id]['stage'] = 'nickname'
                await asyncio.sleep(0.5)
                await message.channel.send("Принято! Теперь напиши свой **игровой никнейм**. **(Шаг 2 из 3)**")
            else:
                await asyncio.sleep(0.5)
                await message.channel.send("Нужно ввести возраст цифрами (например, 18).")
        
        elif stage == 'nickname':
            user_data['nickname'] = message.content
            pending_verification[author_id]['stage'] = 'about'
            await asyncio.sleep(0.5)
            await message.channel.send("Теперь расскажи немного о себе и что планируешь делать на сервере (от 20 до 100 слов). **(Шаг 3 из 3)**")
        
        elif stage == 'about':
            word_count = len(message.content.split())
            if word_count < 20:
                await asyncio.sleep(0.5)
                await message.channel.send(f"Слишком мало. Ты написал всего {word_count} слов. Минимум — 20. Давай ещё раз.")
            elif word_count > 100:
                await asyncio.sleep(0.5)
                await message.channel.send(f"Слишком много. Ты написал {word_count} слов. Максимум — 100. Сократи текст.")
            else:
                user_data['about'] = message.content
                await send_verification_to_admin(message.author, user_data)
                del pending_verification[author_id]
                await asyncio.sleep(0.5)
                await message.channel.send("Готово! Данные отправлены. Жди решения.")
        
        return
    
    await bot.process_commands(message)

async def update_welcome_message(user_id, status):
    if user_id in welcome_messages:
        msg = welcome_messages[user_id]
        embed = msg.embeds[0]
        
        if status == "approved":
            user = bot.get_user(user_id)
            embed.title = f"Добро пожаловать, {user.name if user else 'игрок'}! 🎉"
            embed.description = f"Мы рады приветствовать тебя на сервере Arefulate!\n\n**✅ Заявка одобрена**"
            embed.color = discord.Color.green()
            await msg.edit(content=f"||<@{user_id}>||", embed=embed)
            del welcome_messages[user_id]
            if user_id in verification_attempts:
                del verification_attempts[user_id]
        elif status == "rejected":
            embed.title = f"❌ Заявка отклонена, {bot.get_user(user_id).name if bot.get_user(user_id) else 'игрок'}"
            embed.description = "**Ты можешь попробовать ещё раз, ответь боту.**"
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
        title="🔔 Новая заявка",
        color=discord.Color.orange(),
        timestamp=discord.utils.utcnow()
    )
    embed.set_author(name=str(user), icon_url=user.display_avatar.url)
    embed.add_field(name="Пользователь", value=user.mention, inline=True)
    embed.add_field(name="ID", value=user.id, inline=True)
    embed.add_field(name="Возраст", value=user_data['age'], inline=True)
    embed.add_field(name="Никнейм", value=user_data['nickname'], inline=False)
    embed.add_field(name="О себе", value=user_data['about'][:1024], inline=False)
    embed.add_field(name="Попытка", value=f"{current_attempt}/3", inline=True)

    view = discord.ui.View(timeout=None)
    approve_button = discord.ui.Button(label="✅ Одобрить", style=discord.ButtonStyle.success, custom_id=f"approve_{user.id}")
    reject_button = discord.ui.Button(label="❌ Отклонить", style=discord.ButtonStyle.danger, custom_id=f"reject_{user.id}")
    ban_button = discord.ui.Button(label="⛔ Забанить", style=discord.ButtonStyle.danger, custom_id=f"ban_{user.id}")

    async def button_callback(interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Нет прав.", ephemeral=True)
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
                    
                    await update_welcome_message(user.id, "approved")
                    
                    embed = discord.Embed(
                        title="✅ Заявка одобрена",
                        color=discord.Color.green(),
                        timestamp=discord.utils.utcnow()
                    )
                    embed.add_field(name="Пользователь", value=f"{member.mention} ({str(member)})", inline=False)
                    embed.add_field(name="ID", value=member.id, inline=True)
                    embed.add_field(name="Возраст", value=user_data['age'], inline=True)
                    embed.add_field(name="Никнейм", value=f"**{user_data['nickname']}**", inline=False)
                    embed.add_field(name="О себе", value=user_data['about'][:1024], inline=False)
                    embed.set_footer(text=f"Одобрено: {interaction.user.name}")
                    embed.set_thumbnail(url=member.display_avatar.url)
                    
                    await interaction.response.edit_message(embed=embed, view=None)
                    try:
                        await asyncio.sleep(0.5)
                        await user.send("Добро пожаловать на сервер Arefulate! Твоя заявка одобрена.")
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
                    await user.send("Попытки исчерпаны. Ты забанен на сервере Arefulate.")
                except:
                    pass
                
                try:
                    bot_bans.add(user.id)
                    await member.ban(reason="Исчерпаны попытки.")
                except:
                    pass
                
                embed = discord.Embed(
                    title="🚫 Заявка отклонена — бан",
                    color=discord.Color.dark_red(),
                    timestamp=discord.utils.utcnow()
                )
                embed.add_field(name="Пользователь", value=f"{member.mention} ({str(member)})", inline=False)
                embed.add_field(name="ID", value=member.id, inline=True)
                embed.add_field(name="Возраст", value=user_data['age'], inline=True)
                embed.add_field(name="Никнейм", value=f"**{user_data['nickname']}**", inline=False)
                embed.add_field(name="О себе", value=user_data['about'][:1024], inline=False)
                embed.add_field(name="Статус", value="Забанен (попытки исчерпаны)", inline=False)
                embed.set_footer(text=f"Отклонено: {interaction.user.name}")
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
            embed.add_field(name="ID", value=member.id, inline=True)
            embed.add_field(name="Возраст", value=user_data['age'], inline=True)
            embed.add_field(name="Никнейм", value=f"**{user_data['nickname']}**", inline=False)
            embed.add_field(name="О себе", value=user_data['about'][:1024], inline=False)
            embed.set_footer(text=f"Отклонено: {interaction.user.name}")
            embed.set_thumbnail(url=member.display_avatar.url)
            
            await interaction.response.edit_message(embed=embed, view=None)
            
            try:
                retry_view = discord.ui.View(timeout=300)
                retry_button = discord.ui.Button(label="🔄 Попробовать снова", style=discord.ButtonStyle.primary)
                quit_button = discord.ui.Button(label="🚪 Выйти с сервера", style=discord.ButtonStyle.secondary)
                
                async def retry_callback(retry_interaction):
                    await clear_previous_buttons(user)
                    await retry_interaction.response.edit_message(content=f"Начинаем заново, {user.mention}...", view=None)
                    await restart_verification(user)
                
                async def quit_callback(quit_interaction):
                    await update_welcome_message(user.id, "kicked")
                    await quit_interaction.response.edit_message(content="До свидания. Ты всегда можешь вернуться на сервер.", view=None)
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
                msg = await user.send(f"{user.mention}, твоя заявка отклонена. Можешь попробовать снова или выйти с сервера.", view=retry_view)
                last_bot_messages[user.id] = msg
            except:
                pass
        
        elif interaction.data['custom_id'].startswith("ban"):
            await update_welcome_message(user.id, "banned")
            
            try:
                await asyncio.sleep(0.5)
                await user.send("Ты забанен на сервере Arefulate.")
            except:
                pass
            
            try:
                bot_bans.add(user.id)
                await member.ban(reason=f"Забанен администратором {interaction.user.name}")
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
            embed.add_field(name="ID", value=member.id, inline=True)
            embed.add_field(name="Возраст", value=user_data['age'], inline=True)
            embed.add_field(name="Никнейм", value=f"**{user_data['nickname']}**", inline=False)
            embed.add_field(name="О себе", value=user_data['about'][:1024], inline=False)
            embed.add_field(name="Статус", value="Забанен", inline=False)
            embed.set_footer(text=f"Забанен: {interaction.user.name}")
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