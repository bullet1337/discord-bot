#!/usr/bin/python
import discord

client = discord.Client()
TOKEN = 'MzcwODcyNDAzNDAxOTAwMDMz.DMtZZg.SiNxXQ7nOWhrSTzMk8aFcJxJQIs'
PREFIX = '!test'


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')


@client.event
async def on_message(message):
    if message.content.startswith(PREFIX):
        await client.send_message(message.channel, 'echo:%s' % message.content.replace(PREFIX, '', 1))


@client.event
async def on_voice_state_update(before, after):
    if not before.bot and before.voice.voice_channel != after.voice.voice_channel:
        if client.player:
            client.player.stop()
        print('%s: %s -> %s' % (before.name, before.voice.voice_channel, after.voice.voice_channel))
        if not client.connection.voice_clients:
            client.voice_channel = await client.join_voice_channel(after.voice.voice_channel)
        else:
            await client.voice_channel.move_to(after.voice.voice_channel)
        if after.server_permissions.administrator:
            music = 'https://goxash.tk/arthas.mp3' # 'omae wa - mo shindeiru.mp3'
        else:
            music = 'AND HIS NAME IS - JOHN CENA.mp3'
        client.player = client.voice_channel.create_ffmpeg_player(music)
        client.player.start()


client.voice_channel = None
client.player = None
client.run(TOKEN)
