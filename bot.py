#!/usr/bin/python
import asyncio
import os
import shutil
import urllib
from os import path

from discord.ext import commands
from discord.ext.commands import Bot
from pydub import AudioSegment

AudioSegment.converter = 'ffmpeg.exe'
DBFS = -10

SCRIPT_DIR = path.dirname(path.realpath(__file__))
MUSIC_DIR = path.join(SCRIPT_DIR, 'music')
COMMANDS_DIR = path.join(MUSIC_DIR, 'command')
ENTRANCES_DIR = path.join(MUSIC_DIR, 'entrance')
if not path.exists(MUSIC_DIR):
    os.makedirs(MUSIC_DIR)
    os.makedirs(COMMANDS_DIR)
    os.makedirs(ENTRANCES_DIR)

TOKEN = 'MzcwODcyNDAzNDAxOTAwMDMz.DMtZZg.SiNxXQ7nOWhrSTzMk8aFcJxJQIs'
GREETINGS_DELAY = 0.1
VOLUME = 0.1
bot = Bot(command_prefix=commands.when_mentioned_or('play'))


@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')


@bot.command()
async def echo(message):
    await bot.say('echo:%s' % message)


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


def add_command(command):
    @bot.command(name=command, pass_context=True)
    async def play_command(ctx):
        user = ctx.message.author
        if user.voice_channel:
            if not bot.connection.voice_clients:
                bot.voice_channel = await bot.join_voice_channel(user.voice_channel)
            else:
                await bot.voice_channel.move_to(user.voice_channel)
            bot.player = bot.voice_channel.create_ffmpeg_player(bot.music_commands[command])
            bot.player.volume = VOLUME
            bot.player.start()


@bot.command()
async def add(command, url):
    if not path.exists(url):
        with urllib.request.urlopen(url) as response, open(path.basename(url), 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        url = path.basename(url)

    try:
        extension = os.path.splitext(url)[1][1:].strip().lower()
        file = AudioSegment.from_file(url, extension)
        command_file = path.join(COMMANDS_DIR, path.basename(url))
        shutil.move(url, command_file)
        # file -= file.dBFS - DBFS
        # file.export(command_file, format=extension)
        # os.remove(url)
    except Exception as e:
        print(e)
        await bot.say('Ошибка')
        return

    bot.music_commands[command] = command_file
    add_command(command)
    await bot.say('Добавил команду "%s" для песни "%s"' % (command, os.path.basename(url)))


bot.voice_channel = None
bot.player = None
bot.music_commands = {}
bot.run(TOKEN)