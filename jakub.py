import glob
import os
import random
import re
import time
from collections import defaultdict
from os import path, makedirs

from pydub import AudioSegment

AudioSegment.converter = 'ffmpeg' if os.name == 'posix' else 'ffmpeg.exe'
BASE_DIR = path.join(path.dirname(path.realpath(__file__)), 'jakub')
AUDIO_DIR = path.join(BASE_DIR, 'audio')
if not path.exists(AUDIO_DIR):
    makedirs(AUDIO_DIR)
RES_DIR = path.join(BASE_DIR, 'results')
if not path.exists(RES_DIR):
    makedirs(RES_DIR)
DBFS = -10

audio_files = glob.glob(AUDIO_DIR + os.path.sep + '*.mp3')
audio_map = defaultdict(list)
for file in audio_files:
    number = re.match('([a-z\d]+)[ \.]', path.basename(file)).groups()[0]
    audio_map[number].append(file)


def concat(numbers, outfile):
    infiles = [get_random(audio_map, x) for x in numbers]

    files = [AudioSegment.from_mp3(infile) for infile in infiles]

    result = AudioSegment.empty()
    for file in files:
        file -= file.dBFS - DBFS
        result += file

    file = path.join(RES_DIR, outfile + '_' + str(int(time.time())) + '.mp3')
    result.export(file, format='mp3')
    return file


def jakub_helper(x):
    if audio_map.get(x):
        return [x]
    elif len(x) == 1:
        return None
    else:
        best = len(x) + 1
        best_split = None
        for i in range(1, len(x)):
            first, second = x[:i] + '0' * (len(x) - i), x[i:]
            if second.replace('0', '') == '':
                continue

            first, second = jakub_helper(first), jakub_helper(second)
            if first is None or second is None:
                continue
            else:
                if len(first) + len(second) < best:
                    best = len(first) + len(second)
                    best_split = first
                    best_split.extend(second)
        return None if best == len(x) + 1 else best_split


def case(x):
    strx = ''.join(x)
    if len(strx) >= 2 and strx[-2] == '1':
        return 'pg'
    else:
        if strx[-1] in '234':
            return 'pn'
        elif strx[-1] in '056789':
            return 'pg'
        else:
            return ''


def zero(x, zeros):
    if zeros == 0:
        return x

    for i in range(len(x)):
        number = ''.join(x[i:]) + zeros * '0'
        if number in audio_map:
            rest = [number]
            if number == '1000' and len(x) > 1:
                rest = ['1f'] + rest
            return x[:i] + rest

    rest = ['1' + zeros * '0' + case(x)]
    if rest == '1000' and len(x) > 1:
        rest = ['1f'] + rest

    if all([x in audio_map for x in rest]):
        return x + rest
    else:
        return None


def jakub(x):
    splitted = [y[::-1] for y in [x[::-1][i:i+3] for i in range(0, len(x[::-1]), 3)]][::-1]
    result = [zero(jakub_helper(str(int(y))), (len(splitted) - i - 1) * 3) for i, y in enumerate(splitted)
              if y.replace('0', '') != '' or i == 0]

    if all(result):
        return sum(result, [])


def get_random(audio_map, number):
    return audio_map[number][random.randrange(0, len(audio_map[number]))]


def seidisnilyu(a):
    if a:
        if a.isdigit():
            result = jakub(str(int(a)))
            if result:
                print(result)
                return concat(result, str(a))
            else:
                error = 'noon'
        else:
            error = 'error'
    else:
        error = 'empty'

    if error:
        return path.join(AUDIO_DIR, error + '.mp3')