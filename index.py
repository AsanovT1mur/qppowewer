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

@bot.event
async def on_ready():
    print(f'Бот {bot.user} успешно запущен и готов к работе!')

@bot.event
async def on_member_join(member):
    welcome_channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if welcome_channel:
        embed = discord.Embed(
            title=f"Добро пожаловать, {member.name}! 🎉",
            description=f"Мы рады приветствовать тебя на сервере Arefulate!\n"
                        f"**Пожалуйста, пройди быструю авторизацию, отправив мне личное сообщение (ЛС). Это необходимо для начала общения!**",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await welcome_channel.send(content=member.mention, embed=embed)
    
    try:
        embed = discord.Embed(
            title="Авторизация на сервере",
            description="Привет! Для доступа к серверу, пожалуйста, ответь на несколько вопросов.\n"
                        "**Шаг 1 из 3** — Введи свой **возраст** (только число).",
            color=discord.Color.blue()
        )
        await member.send(embed=embed)
        pending_verification[member.id] = {'stage': 'age', 'data': {}}
    except discord.Forbidden:
        if welcome_channel:
            await welcome_channel.send(f"{member.mention}, не могу отправить тебе личное сообщение. "
                                        f"Пожалуйста, открой ЛС для получения авторизации.")
            
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
                user_data['age'] = int(message.content)
                pending_verification[author_id]['stage'] = 'nickname'
                await message.channel.send("Отлично! Теперь введи свой **игровой никнейм**. **(Шаг 2 из 3)**")
            else:
                await message.channel.send("Пожалуйста, введи возраст числом (например, 18).")
        
        elif stage == 'nickname':
            user_data['nickname'] = message.content
            pending_verification[author_id]['stage'] = 'about'
            await message.channel.send("Расскажи немного о себе и о том, что планируешь делать на сервере (минимум 20 слов, максимум 100). **(Шаг 3 из 3)**")
        
        elif stage == 'about':
            word_count = len(message.content.split())
            if word_count < 20:
                await message.channel.send(f"Слишком коротко. Ты написал всего {word_count} слов. Нужно минимум 20. Попробуй ещё раз.")
            elif word_count > 100:
                await message.channel.send(f"Слишком длинно. Ты написал {word_count} слов. Нужно не больше 100. Сократи и отправь снова.")
            else:
                user_data['about'] = message.content
                await send_verification_to_admin(message.author, user_data)
                del pending_verification[author_id]
                await message.channel.send("Спасибо! Твои данные отправлены администратору. Ожидай подтверждения.")
        
        return
    
    await bot.process_commands(message)

@bot.command(name='adminlist')
@commands.has_permissions(administrator=True)
async def send_admin_list_command(ctx):
    embed = discord.Embed(
        title="👑 Администрация сервера Arefulate",
        description="Свяжитесь с нами, если у вас есть вопросы или предложения. Мы всегда рады помочь!",
        color=discord.Color.gold(),
        timestamp=discord.utils.utcnow()
    )
    embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else bot.user.display_avatar.url)
    
    embed.add_field(name="👤 Владельцы", value="**MrKekmen, Drxsa**", inline=False)
    embed.add_field(name="🛡️ Главный администратор", value="**Не назначен**", inline=False)
    embed.add_field(name="⚙️ Технический администратор", value="**VoidWalker2042**", inline=False)
    embed.set_footer(text="Arefulate Staff • Обновлено")
    
    await ctx.send(embed=embed)
    await ctx.message.delete()

async def send_verification_to_admin(user, user_data):
    admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
    if not admin_channel:
        print(f"Ошибка: Канал с ID {ADMIN_CHANNEL_ID} не найден!")
        return
    
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

    view = discord.ui.View(timeout=None)
    approve_button = discord.ui.Button(label="✅ Одобрить", style=discord.ButtonStyle.success, custom_id=f"approve_{user.id}")
    reject_button = discord.ui.Button(label="❌ Отклонить и забанить", style=discord.ButtonStyle.danger, custom_id=f"reject_{user.id}")

    async def button_callback(interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Недостаточно прав. Требуются права администратора.", ephemeral=True)
            return
        
        member = interaction.guild.get_member(user.id)
        if not member:
            await interaction.response.send_message("Пользователь не найден на сервере.", ephemeral=True)
            return
        
        if interaction.data['custom_id'].startswith("approve"):
            role = discord.utils.get(interaction.guild.roles, name="Игрок")
            if role:
                try:
                    await member.add_roles(role)
                    
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
                        await user.send("Поздравляю! Твоя заявка одобрена. Добро пожаловать на сервер!")
                    except:
                        pass
                except discord.Forbidden:
                    await interaction.response.send_message("У бота нет прав для выдачи роли.", ephemeral=True)
            else:
                await interaction.response.send_message("Роль 'Игрок' не найдена на сервере.", ephemeral=True)
        
        elif interaction.data['custom_id'].startswith("reject"):
            try:
                try:
                    await user.send("К сожалению, твоя заявка была отклонена. Ты был забанен на сервере.")
                except:
                    pass
                
                await member.ban(reason=f"Заявка отклонена администратором {interaction.user.name}")
                
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
                embed.add_field(name="Статус", value="Забанен", inline=False)
                embed.set_footer(text=f"Отклонено администратором {interaction.user.name}")
                embed.set_thumbnail(url=member.display_avatar.url)
                
                await interaction.response.edit_message(embed=embed, view=None)
            
            except discord.Forbidden:
                await interaction.response.send_message("У бота нет прав для бана пользователя.", ephemeral=True)
            except discord.NotFound:
                await interaction.response.send_message("Пользователь покинул сервер до обработки заявки.", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"Ошибка при бане: {str(e)}", ephemeral=True)

    approve_button.callback = button_callback
    reject_button.callback = button_callback
    
    view.add_item(approve_button)
    view.add_item(reject_button)
    
    await admin_channel.send(embed=embed, view=view)

bot.run(BOT_TOKEN)