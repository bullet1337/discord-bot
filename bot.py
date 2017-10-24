#!/usr/bin/python
import asyncio
import json
import os
import re
import shutil
from os import path
from urllib import request

import editdistance as editdistance
import youtube_dl as youtube_dl
from discord import Member
from discord.ext import commands
from discord.ext.commands import Bot
from pydub import AudioSegment

from jakub import seidisnilyu


class MusicBot(Bot):
    SCRIPT_DIR = path.dirname(path.realpath(__file__))
    CONFIG_PATH = path.join(SCRIPT_DIR, 'config.json')
    GREETINGS_DELAY = 0.1
    VOLUME_STEP = 0.1
    TOKEN = 'MzcwODcyNDAzNDAxOTAwMDMz.DMtZZg.SiNxXQ7nOWhrSTzMk8aFcJxJQIs'
    ADMIN_IDS = ['263783673344557089', '239737410932572160', '242716686791344129']

    def __init__(self, command_prefix, **options):
        super().__init__(command_prefix, formatter=None, description=None, pm_help=False, **options)
        AudioSegment.converter = 'ffmpeg.exe'

        self.voice_channel = None
        self.volume = 0.3
        self.player = None
        self.music_commands = {}

        cfg = MusicBot.load_cfg()
        self.MUSIC_DIR = path.join(MusicBot.SCRIPT_DIR, cfg.get('MUSIC_DIR', 'music'))
        self.COMMANDS_DIR = path.join(self.MUSIC_DIR, cfg.get('COMMANDS_DIR', 'command'))
        self.USERS_DIR = path.join(self.MUSIC_DIR, cfg.get('USERS_DIR', 'users'))
        if not path.exists(self.MUSIC_DIR):
            os.makedirs(self.MUSIC_DIR)
            os.makedirs(self.COMMANDS_DIR)
            os.makedirs(self.USERS_DIR)
        for command in cfg.get('commands', []):
            if command['type'] == 'command':
                self.music_commands[command['command']] = path.join(self.COMMANDS_DIR, command['file'])
                self.add_music_command(command['command'])
        self.users_music = cfg.get('users', {})

    @staticmethod
    def check_user(ctx):
        return ctx.message.author.id in MusicBot.ADMIN_IDS

    async def save_cfg(self):
        cfg = {
            'MUSIC_DIR': path.basename(self.MUSIC_DIR),
            'COMMANDS_DIR': path.basename(self.COMMANDS_DIR),
            'USERS_DIR': path.basename(self.USERS_DIR),
            'commands': [
                {'type': 'command', 'command': command, 'file': os.path.basename(file)}
                for command, file in self.music_commands.items()
            ],
            'users': self.users_music
        }

        with open(MusicBot.CONFIG_PATH, mode='w', encoding='utf8') as file:
            json.dump(cfg, file, indent=4)

    @staticmethod
    def load_cfg():
        if os.path.exists(MusicBot.CONFIG_PATH):
            with open(MusicBot.CONFIG_PATH, mode='r', encoding='utf8') as file:
                return json.load(file)
        else:
            return {}

    async def join_channel(self, channel):
        if not self.connection.voice_clients:
            self.voice_channel = await self.join_voice_channel(channel)
        else:
            await self.voice_channel.move_to(channel)

    def run(self):
        super(MusicBot, self).run(MusicBot.TOKEN)

    def add_music_command(self, command):
        @self.command(name=command, pass_context=True)
        async def play_command(ctx):
            await self.play(ctx.message.author.voice_channel, self.music_commands[command])

    def get_volume_str(self):
        volumes = int(self.volume / 0.1)
        return '[' + '=' * volumes + '   ' * (20 - volumes) + '] %d%%' % (round(self.volume * 100))

    def check_music_url(self, url):
        if not path.exists(url):
            if path.exists(path.join(self.COMMANDS_DIR, path.basename(url))):
                url = path.join(self.COMMANDS_DIR, path.basename(url))
            else:
                try:
                    if 'youtube' in url:
                        ydl_opts = {
                            'format': 'bestaudio/best',
                            'postprocessors': [
                                {
                                    'key': 'FFmpegExtractAudio',
                                    'preferredcodec': 'mp3',
                                    'preferredquality': '320',
                                }
                            ],
                            'outtmpl': path.basename(url).replace('?', '_') + '.%(ext)s'
                        }
                        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([url])
                        url = '%s.%s' % (path.splitext(ydl_opts['outtmpl'])[0],
                                         ydl_opts['postprocessors'][0]['preferredcodec'])
                    else:
                        with request.urlopen(url) as response, open(path.basename(url), 'wb') as out_file:
                            shutil.copyfileobj(response, out_file)
                        url = path.basename(url)
                except Exception as e:
                    print(e)
                    return None

        try:
            extension = os.path.splitext(url)[1][1:].strip().lower()
            AudioSegment.from_file(url, extension)
            return url
        except Exception as e:
            print(e)
            return None

    async def play(self, channel, file):
        if channel:
            if self.player:
                self.player.stop()

            await self.join_channel(channel)

            self.player = self.voice_channel.create_ffmpeg_player(file)
            self.player.volume = self.volume
            self.player.start()

    async def add_user_music(self, user, url, intro=True):
        url = self.check_music_url(url)
        if url is None:
            await self.say('Ошибка')
        else:
            suffix = 'intro' if intro else 'outro'
            user_file = path.join(self.USERS_DIR, '%s_%s.mp3' % (user.id, suffix))
            if path.dirname(url) == self.COMMANDS_DIR:
                shutil.copy2(url, user_file)
            else:
                shutil.move(url, user_file)
            user_music = self.users_music.get(user.id)
            if user_music:
                user_music[suffix] = user_file
            else:
                self.users_music[user.id] = {suffix: user_file}
            await self.say('%s %s для пользователя "%s" добавлено' % (suffix, path.basename(url), user.name))
            await self.save_cfg()


def create_bot():
    bot = MusicBot(command_prefix=commands.when_mentioned_or('!'))

    @bot.event
    async def on_ready():
        print('Logged in as')
        print(bot.user.name)
        print(bot.user.id)
        print('------')

    @bot.event
    async def on_voice_state_update(before, after):
        if not before.bot and before.voice_channel != after.voice_channel:
            if bot.player:
                bot.player.stop()
            print('%s: %s -> %s' % (before.name, before.voice_channel, after.voice_channel))

            await bot.join_channel(after.voice_channel or before.voice_channel)

            user_music = bot.users_music.get(before.id)
            if user_music:
                user_music = user_music.get('intro' if after.voice_channel else 'outro')
                if user_music:
                    bot.player = bot.voice_channel.create_ffmpeg_player(user_music)
                    bot.player.volume = bot.volume
                    await asyncio.sleep(MusicBot.GREETINGS_DELAY)
                    bot.player.start()

    @bot.command()
    @commands.check(MusicBot.check_user)
    async def intro(user: Member, url):
        await bot.add_user_music(user, url, True)

    @bot.command()
    @commands.check(MusicBot.check_user)
    async def outro(user: Member, url):
        await bot.add_user_music(user, url, False)

    @bot.command()
    async def echo(message):
        await bot.say('echo:%s' % message)

    @bot.command()
    @commands.check(MusicBot.check_user)
    async def vu():
        bot.volume += MusicBot.VOLUME_STEP

        if bot.volume > 2.0:
            bot.volume = 2.0
            await bot.say('Максимальная громкость')
        await bot.say(bot.get_volume_str())

    @bot.command()
    @commands.check(MusicBot.check_user)
    async def vd():
        bot.volume -= MusicBot.VOLUME_STEP

        if bot.volume <= 0:
            bot.volume = 0
            await bot.say('Бота не слышно')
        await bot.say(bot.get_volume_str())

    @bot.command()
    @commands.check(MusicBot.check_user)
    async def stop():
        if bot.player:
            bot.player.stop()

    @bot.command()
    async def v():
        await bot.say(bot.get_volume_str())

    @bot.command()
    @commands.check(MusicBot.check_user)
    async def add(command, url):
        url = bot.check_music_url(url)
        if url is None:
            await bot.say('Ошибка')
            return

        command_file = path.join(bot.COMMANDS_DIR, path.basename(url))
        shutil.move(url, command_file)

        if command not in bot.commands:
            bot.music_commands[command] = command_file
            bot.add_music_command(command)
            await bot.say('Добавил команду "%s" для песни "%s"' % (command, os.path.basename(url)))
            await bot.save_cfg()
        else:
            await bot.say('Команда "%s" уже добавлена' % command)

    @bot.command()
    @commands.check(MusicBot.check_user)
    async def remove(command):
        if bot.remove_command(command):
            bot.music_commands.pop(command, None)
            await bot.say('Команада "%s" удалена' % command)
            await bot.save_cfg()
        else:
            await bot.say('Команда "%s" не найдена' % command)

    @bot.command()
    async def list():
        await bot.say('Список команд:\n%s' % '\t'.join(sorted(bot.music_commands)) if bot.music_commands else
                      'Список команд пуст')

    @bot.command(pass_context=True)
    async def jakub(ctx, a):
        await bot.play(ctx.message.author.voice_channel, seidisnilyu(a))

    @bot.event
    async def on_command_error(event_method, ctx):
        command = re.sub(r'([aeuioауеэоаыяию])+$', r'\1', ctx.invoked_with)
        command = min(ctx.bot.music_commands.keys(), key=lambda x: editdistance.eval(command, x))
        await bot.play(ctx.message.author.voice_channel, ctx.bot.music_commands[command])

    return bot

if __name__ == '__main__':
    create_bot().run()
