#!/usr/bin/python
import asyncio

from discord.ext import commands
from discord.ext.commands import Bot

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

bot.voice_channel = None
bot.player = None
bot.run(TOKEN)