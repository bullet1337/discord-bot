#!/usr/bin/python3.5
import asyncio
import json
import os
import random
import re
import shutil
import time
from collections import defaultdict
from datetime import datetime
from os import path
from urllib import request

import editdistance as editdistance
import youtube_dl as youtube_dl
from discord import ChannelType
from discord import Member
from discord.ext import commands
from discord.ext.commands import Bot
from gtts import gTTS
from pydub import AudioSegment
from transliterate import translit

from jakub import seidisnilyu


class MusicBot(Bot):
    SCRIPT_DIR = path.dirname(path.realpath(__file__))
    CONFIG_PATH = path.join(SCRIPT_DIR, 'config.json')
    LEVENSHTEIN_THRESHOLD = 6
    SWITCH_TIME = 5
    GREETINGS_DELAY = 0.1
    VOLUME_STEP = 0.1
    DBFS = -10
    warnings_map = {
        1: 'ugomonis',
        2: 'ostanovis',
        3: 'final'
    }

    def __init__(self, command_prefix, **options):
        super().__init__(command_prefix, formatter=None, description=None, pm_help=False, **options)
        AudioSegment.converter = 'ffmpeg' if os.name == 'posix' else 'ffmpeg.exe'

        self.follow_id = None
        self.voice_channel = None
        self.volume = 0.3
        self.player = None
        self.music_commands = {}
        self.users_entries = {}
        self.users_warnings = defaultdict(int)

        cfg = MusicBot.load_cfg()
        self.TOKEN = cfg['TOKEN']
        MusicBot.ADMIN_IDS = cfg['ADMIN_IDS']
        self.MUSIC_DIR = path.join(MusicBot.SCRIPT_DIR, cfg.get('MUSIC_DIR', 'music'))
        self.COMMANDS_DIR = path.join(self.MUSIC_DIR, cfg.get('COMMANDS_DIR', 'command'))
        self.USERS_DIR = path.join(self.MUSIC_DIR, cfg.get('USERS_DIR', 'users'))
        self.UTILS_DIR = path.join(self.MUSIC_DIR, 'utils')
        if not path.exists(self.COMMANDS_DIR):
            os.makedirs(self.COMMANDS_DIR)
        if not path.exists(self.USERS_DIR):
            os.makedirs(self.USERS_DIR)
        for command in cfg.get('commands', []):
            if command['type'] == 'command' and path.exists(path.join(self.COMMANDS_DIR, command['file'])):
                self.music_commands[command['command']] = path.join(self.COMMANDS_DIR, command['file'])
                self.add_music_command(command['command'])
        music_files = set(self.music_commands.values())
        for file in os.listdir(self.COMMANDS_DIR):
            file = path.join(self.COMMANDS_DIR, file)
            if path.isfile(file):
                command = os.path.splitext(os.path.basename(file))[0]
                if command not in self.music_commands and file not in music_files \
                        and not re.findall('[ \t\n]', command):
                    self.music_commands[command] = file
                    self.add_music_command(command)

        self.users_music = cfg.get('users', {})
        for file in os.listdir(self.USERS_DIR):
            file = path.join(self.USERS_DIR, file)
            if path.isfile(file):
                command = os.path.splitext(os.path.basename(file))[0].split('_')
                if len(command) == 2:
                    user_id = command[0]
                    type = command[1]
                    if user_id not in self.users_music or type not in self.users_music[user_id]:
                        if user_id not in self.users_music:
                            self.users_music[user_id] = {}

                        self.users_music[user_id][type] = os.path.basename(file)

        self.save_cfg()

    @staticmethod
    def check_user(ctx):
        return ctx.message.author.id in MusicBot.ADMIN_IDS

    def save_cfg(self):
        cfg = {
            'TOKEN': self.TOKEN,
            'ADMIN_IDS': self.ADMIN_IDS,
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
            json.dump(cfg, file, indent=4, ensure_ascii=False)

    @staticmethod
    def load_cfg():
        if os.path.exists(MusicBot.CONFIG_PATH):
            with open(MusicBot.CONFIG_PATH, mode='r', encoding='utf8') as file:
                return json.load(file)
        else:
            return {}

    async def join_channel(self, channel):
        if self.voice_channel == channel:
            return

        if self.follow_id:
            found = False
            for x_channel in self.get_all_channels():
                if x_channel.type == ChannelType.voice:
                    for member in x_channel.voice_members:
                        if member.id == self.follow_id:
                            channel = x_channel
                            found = True
                            break
                    if found:
                        break

        if not self.connection.voice_clients:
            try:
                self.voice_channel = await self.join_voice_channel(channel)
            except TimeoutError:
                return
        else:
            await self.voice_channel.move_to(channel)

    def run(self):
        super(MusicBot, self).run(self.TOKEN)

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

    async def tts(self, channel, text):
        temp_file = path.join(self.UTILS_DIR, '%d.mp3' % random.randint(0, 10000))
        gTTS(text=text, lang='ru').save(temp_file)
        await self.play(channel, temp_file, True)

    async def play(self, channel, file, delete=False):
        if channel:
            if self.player:
                self.player.stop()

            await self.join_channel(channel)

            self.player = self.voice_channel.create_ffmpeg_player(file,
                                                                  after=(lambda: os.remove(file)) if delete else None)
            self.player.volume = self.volume
            self.player.start()

    async def add_user_music(self, user, url, intro=True):
        url = self.check_music_url(url) or self.check_music_url(self.music_commands[url])
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
                user_music[suffix] = path.basename(user_file)
            else:
                self.users_music[user.id] = {suffix: path.basename(user_file)}
            await self.say('%s %s для пользователя "%s" добавлено' % (suffix, path.basename(url), user.name))
            self.save_cfg()

    async def remove_user_music(self, user, intro=True):
        suffix = 'intro' if intro else 'outro'
        if user.id in self.users_music and suffix in self.users_music[user.id]:
            #os.remove(path.join(self.USERS_DIR, '%s_%s.mp3' % (user.id, suffix)))
            await self.say('%s для пользователя "%s" удалено' % (suffix, user.name))
            self.users_music[user.id].pop(suffix)

            if not self.users_music[user.id]:
                self.users_music.pop(user.id)

        self.save_cfg()

    def concat(self, infiles, outfile):
        files = [AudioSegment.from_mp3(infile) for infile in infiles if path.exists(infile)]

        result = AudioSegment.empty()
        for file in files:
            file -= file.dBFS - MusicBot.DBFS
            result += file

        result.export(outfile, format='mp3')
        return outfile

    def create_phrase(self, template, data):
        temp_file = path.join(self.UTILS_DIR, '%d_%d.mp3' % (random.randint(0, 10000), int(round(time.time() * 1000))))
        gTTS(text=data, lang='ru').save(temp_file)
        return self.concat(
            [
                path.join(self.UTILS_DIR, '%s_prefix.mp3' % template),
                temp_file,
                path.join(self.UTILS_DIR, '%s_suffix.mp3' % template)
            ],
            temp_file
        )


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
            if after.voice_channel:
                last_entry = bot.users_entries.get(after.voice_channel)
                bot.users_entries[after.voice_channel] = datetime.now()
                if last_entry and (bot.users_entries[after.voice_channel] - last_entry).seconds <= MusicBot.SWITCH_TIME:
                    bot.users_warnings[after.id] += 1
                    if bot.users_warnings[after.id] >= len(MusicBot.warnings_map):
                        bot.users_warnings[after.id] = 1
                    await bot.play(after.voice_channel,
                                   bot.create_phrase(bot.warnings_map[bot.users_warnings[after.id]], after.name),
                                   True)
                    return

            if bot.player:
                bot.player.stop()
            print('%s: %s -> %s' % (before.name, before.voice_channel, after.voice_channel))

            await bot.join_channel(after.voice_channel or before.voice_channel)

            user_music = bot.users_music.get(before.id)
            await asyncio.sleep(MusicBot.GREETINGS_DELAY)
            if user_music:
                user_music = user_music.get('intro' if after.voice_channel else 'outro')
                if user_music:
                    bot.player = bot.voice_channel.create_ffmpeg_player(path.join(bot.USERS_DIR, user_music))
                    bot.player.volume = bot.volume
                    bot.player.start()
                    return

            await bot.tts(after.voice_channel or before.voice_channel,
                          '%s %s' % ('Привет' if after.voice_channel else 'Пока', after.name))

    @bot.command()
    @commands.check(MusicBot.check_user)
    async def follow(user: Member):
        if user.voice_channel:
            await bot.join_channel(user.voice_channel)
        bot.follow_id = user.id

    @bot.command()
    @commands.check(MusicBot.check_user)
    async def unfollow():
        bot.follow_id = None

    @bot.command()
    @commands.check(MusicBot.check_user)
    async def intro(user: Member, url):
        await bot.add_user_music(user, url, True)

    @bot.command()
    @commands.check(MusicBot.check_user)
    async def outro(user: Member, url):
        await bot.add_user_music(user, url, False)

    @bot.command()
    @commands.check(MusicBot.check_user)
    async def rintro(user: Member):
        await bot.remove_user_music(user, True)

    @bot.command()
    @commands.check(MusicBot.check_user)
    async def routro(user: Member):
        await bot.remove_user_music(user, False)

    @bot.command()
    async def echo(message):
        await bot.say('echo:%s' % message)

    @bot.command(pass_context=True)
    @commands.check(MusicBot.check_user)
    async def tts(ctx):
        await bot.tts(ctx.message.author.voice_channel,
                      ctx.message.clean_content.replace(ctx.prefix + ctx.invoked_with, '').strip())

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
    async def vs(message):
        if message.isdigit():
            volume = int(message)
            if 0 <= volume <= 200:
                bot.volume = volume / 100
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
    async def reboot():
        exit(0)

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
            bot.save_cfg()
        else:
            await bot.say('Команда "%s" уже добавлена' % command)

    @bot.command()
    @commands.check(MusicBot.check_user)
    async def remove(command):
        if bot.remove_command(command):
            bot.music_commands.pop(command, None)
            await bot.say('Команада "%s" удалена' % command)
            bot.save_cfg()
        else:
            await bot.say('Команда "%s" не найдена' % command)

    @bot.command()
    async def list():
        await bot.say('Список команд:\n%s' % '\t'.join(sorted(bot.music_commands)) if bot.music_commands else
                      'Список команд пуст')

    @bot.command(pass_context=True)
    async def jakub(ctx, a):
        file = seidisnilyu(a)
        await bot.play(ctx.message.author.voice_channel, file, True and path.basename(path.dirname(file)) != 'audio')

    @bot.event
    async def on_command_error(event_method, ctx):
        command = re.sub(r'([aeuioауеэоаыяию])+$', r'\1', ctx.invoked_with, flags=re.IGNORECASE)
        command1 = min(ctx.bot.music_commands.keys(), key=lambda x: editdistance.eval(command, x))
        min1 = editdistance.eval(command, command1)

        command = translit(command, 'ru', reversed=re.fullmatch('[а-яА-Я0-9 -_]+', command))
        command2 = min(ctx.bot.music_commands.keys(), key=lambda x: editdistance.eval(command, x))
        min2 = editdistance.eval(command, command2)

        if min(min1, min2) <= 3:
            await bot.play(ctx.message.author.voice_channel,
                           ctx.bot.music_commands[command1 if min1 <= min2 else command2])

    return bot

if __name__ == '__main__':
    create_bot().run()
