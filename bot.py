#!/usr/bin/python
import os
import shutil
from os import path
from urllib import request

from discord.ext import commands
from discord.ext.commands import Bot
from pydub import AudioSegment

from utils import add_music_command, init_bot, save_cfg

AudioSegment.converter = 'ffmpeg.exe'

TOKEN = 'MzcwODcyNDAzNDAxOTAwMDMz.DMtZZg.SiNxXQ7nOWhrSTzMk8aFcJxJQIs'
ADMIN_IDS = ['263783673344557089', '239737410932572160']
GREETINGS_DELAY = 0.1
bot = Bot(command_prefix=commands.when_mentioned_or('!'))
init_bot(bot)


def check_user(ctx):
    return ctx.message.author.id in ADMIN_IDS


@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')


@bot.command()
async def echo(message):
    await bot.say('echo:%s' % message)

"""
@bot.event
async def on_voice_state_update(before, after):
    if not before.bot and after.voice.voice_channel and before.voice.voice_channel != after.voice.voice_channel:
        if bot.player:
            bot.player.stop()
        print('%s: %s -> %s' % (before.name, before.voice.voice_channel, after.voice.voice_channel))
        if not bot.connection.voice_clients:
            bot.voice_channel = await bot.join_voice_channel(after.voice.voice_channel)
        else:
            await bot.voice_channel.move_to(after.voice.voice_channel)
        if after.server_permissions.administrator:
            music = 'https://goxash.tk/arthas.mp3' # 'omae wa - mo shindeiru.mp3'
        else:
            music = 'AND HIS NAME IS - JOHN CENA.mp3'
        bot.player = bot.voice_channel.create_ffmpeg_player(music)
        bot.player.volume = VOLUME
        await asyncio.sleep(GREETINGS_DELAY)
        bot.player.start()
"""


@bot.command()
@commands.check(check_user)
async def add(command, url):
    if not path.exists(url):
        if path.exists(path.join(bot.COMMANDS_DIR, path.basename(url))):
            url = path.join(bot.COMMANDS_DIR, path.basename(url))
        else:
            with request.urlopen(url) as response, open(path.basename(url), 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
            url = path.basename(url)

    try:
        extension = os.path.splitext(url)[1][1:].strip().lower()
        AudioSegment.from_file(url, extension)
        command_file = path.join(bot.COMMANDS_DIR, path.basename(url))
        shutil.move(url, command_file)
    except Exception as e:
        print(e)
        await bot.say('Ошибка')
        return

    if command not in bot.commands:
        bot.music_commands[command] = command_file
        add_music_command(bot, command)
        await bot.say('Добавил команду "%s" для песни "%s"' % (command, os.path.basename(url)))
        await save_cfg(bot)
    else:
        await bot.say('Команда "%s" уже добавлена' % command)


@bot.command()
@commands.check(check_user)
async def remove(command):
    if bot.remove_command(command):
        bot.music_commands.pop(command, None)
        await bot.say('Команада "%s" удалена' % command)
        await save_cfg(bot)
    else:
        await bot.say('Команда "%s" не найдена' % command)


@bot.command()
async def list():
    if bot.music_commands:
        msg = 'Список команд:\n'
    else:
        await bot.say('Список команд пуст')
        return

    for command in sorted(bot.music_commands):
        msg += '\t%s: "%s"\n' % (command, path.basename(bot.music_commands[command]))

    await bot.say(msg)

bot.run(TOKEN)
