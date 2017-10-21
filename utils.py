import json
import os
from os import path

VOLUME = 0.1
SCRIPT_DIR = path.dirname(path.realpath(__file__))
CONFIG_PATH = path.join(SCRIPT_DIR, 'config.json')


def add_music_command(bot, command):
    @bot.command(name=command, pass_context=True)
    async def play_command(ctx):
        user = ctx.message.author
        if user.voice_channel:
            if bot.player:
                bot.player.stop()

            if not bot.connection.voice_clients:
                bot.voice_channel = await bot.join_voice_channel(user.voice_channel)
            else:
                await bot.voice_channel.move_to(user.voice_channel)

            bot.player = bot.voice_channel.create_ffmpeg_player(bot.music_commands[command])
            bot.player.volume = VOLUME
            bot.player.start()


async def save_cfg(bot):
    cfg = {
        'MUSIC_DIR': path.basename(bot.MUSIC_DIR),
        'COMMANDS_DIR': path.basename(bot.COMMANDS_DIR),
        'ENTRANCES_DIR': path.basename(bot.ENTRANCES_DIR),
        'commands': [
            {'type': 'command', 'command': command, 'file': os.path.basename(file)}
            for command, file in bot.music_commands.items()
        ]
    }

    with open(CONFIG_PATH, mode='w', encoding='utf8') as file:
        json.dump(cfg, file, indent=4)


def load_cfg():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, mode='r', encoding='utf8') as file:
            return json.load(file)
    else:
        return {}


def init_bot(bot):
    bot.voice_channel = None
    bot.player = None
    bot.music_commands = {}

    cfg = load_cfg()
    bot.MUSIC_DIR = path.join(SCRIPT_DIR, cfg.get('MUSIC_DIR', 'music'))
    bot.COMMANDS_DIR = path.join(bot.MUSIC_DIR, cfg.get('COMMANDS_DIR', 'command'))
    bot.ENTRANCES_DIR = path.join(bot.MUSIC_DIR, cfg.get('ENTRANCES_DIR', 'entrance'))
    if not path.exists(bot.MUSIC_DIR):
        os.makedirs(bot.MUSIC_DIR)
        os.makedirs(bot.COMMANDS_DIR)
        os.makedirs(bot.ENTRANCES_DIR)
    for command in cfg.get('commands', []):
        if command['type'] == 'command':
            bot.music_commands[command['command']] = path.join(bot.COMMANDS_DIR, command['file'])
            add_music_command(bot, command['command'])