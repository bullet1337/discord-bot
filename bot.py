#!/usr/bin/python
import asyncio
import json
import os
import shutil
from os import path
from urllib import request

from discord.ext import commands
from discord.ext.commands import Bot
from pydub import AudioSegment


class MusicBot(Bot):
    SCRIPT_DIR = path.dirname(path.realpath(__file__))
    CONFIG_PATH = path.join(SCRIPT_DIR, 'config.json')
    GREETINGS_DELAY = 0.1
    VOLUME_STEP = 0.1
    TOKEN = 'MzcwODcyNDAzNDAxOTAwMDMz.DMtZZg.SiNxXQ7nOWhrSTzMk8aFcJxJQIs'
    ADMIN_IDS = ['263783673344557089', '239737410932572160', '242716686791344129']

    def __init__(self, command_prefix, formatter=None, description=None, pm_help=False, **options):
        super().__init__(command_prefix, formatter=None, description=None, pm_help=False, **options)
        AudioSegment.converter = 'ffmpeg.exe'

        self.voice_channel = None
        self.volume = 0.3
        self.player = None
        self.music_commands = {}

        cfg = MusicBot.load_cfg()
        self.MUSIC_DIR = path.join(MusicBot.SCRIPT_DIR, cfg.get('MUSIC_DIR', 'music'))
        self.COMMANDS_DIR = path.join(self.MUSIC_DIR, cfg.get('COMMANDS_DIR', 'command'))
        self.ENTRANCES_DIR = path.join(self.MUSIC_DIR, cfg.get('ENTRANCES_DIR', 'entrance'))
        if not path.exists(self.MUSIC_DIR):
            os.makedirs(self.MUSIC_DIR)
            os.makedirs(self.COMMANDS_DIR)
            os.makedirs(self.ENTRANCES_DIR)
        for command in cfg.get('commands', []):
            if command['type'] == 'command':
                self.music_commands[command['command']] = path.join(self.COMMANDS_DIR, command['file'])
                self.add_music_command(command['command'])

    @staticmethod
    def check_user(ctx):
        return ctx.message.author.id in MusicBot.ADMIN_IDS

    async def save_cfg(self):
        cfg = {
            'MUSIC_DIR': path.basename(self.MUSIC_DIR),
            'COMMANDS_DIR': path.basename(self.COMMANDS_DIR),
            'ENTRANCES_DIR': path.basename(self.ENTRANCES_DIR),
            'commands': [
                {'type': 'command', 'command': command, 'file': os.path.basename(file)}
                for command, file in self.music_commands.items()
                ]
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
            user = ctx.message.author
            if user.voice_channel:
                if self.player:
                    self.player.stop()

                await self.join_channel(user.voice_channel)

                self.player = self.voice_channel.create_ffmpeg_player(self.music_commands[command])
                self.player.volume = self.volume
                self.player.start()

    def get_volume_str(self):
        volumes = int(self.volume / 0.1)
        return '[' + '=' * volumes + '   ' * (20 - volumes) + '] %d%%' % (round(self.volume * 100))


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

            if after.server_permissions.administrator:
                music = 'https://goxash.tk/sounds/arthas.mp3'  # 'omae wa - mo shindeiru.mp3'
            elif after.id == '263783673344557089':
                music = os.path.join(bot.ENTRANCES_DIR, 'bullet.mp3' if after.voice_channel else 'vse.mp3')
            else:
                music = os.path.join(bot.ENTRANCES_DIR,
                                     'AND HIS NAME IS - JOHN CENA.mp3' if after.voice_channel else 'vse.mp3')
            bot.player = bot.voice_channel.create_ffmpeg_player(music)
            bot.player.volume = bot.volume
            await asyncio.sleep(MusicBot.GREETINGS_DELAY)
            bot.player.start()

    @bot.command()
    async def echo(message):
        await bot.say('echo:%s' % message)

    @bot.command()
    async def vu():
        bot.volume += MusicBot.VOLUME_STEP

        if bot.volume > 2.0:
            bot.volume = 2.0
            await bot.say('Максимальная громкость')
        await bot.say(bot.get_volume_str())

    @bot.command()
    async def vd():
        bot.volume -= MusicBot.VOLUME_STEP

        if bot.volume <= 0:
            bot.volume = 0
            await bot.say('Бота не слышно')
        await bot.say(bot.get_volume_str())

    @bot.command()
    async def stop():
        if bot.player:
            bot.player.stop()

    @bot.command()
    async def v():
        await bot.say(bot.get_volume_str())

    @bot.command()
    @commands.check(MusicBot.check_user)
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

    return bot

if __name__ == '__main__':
    create_bot().run()
# TODO VOLUME
# TODO INTRO OUTRO
# TODO JAKUB
