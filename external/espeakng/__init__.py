#!/usr/bin/env python
# -*- coding: utf-8 -*- 

#
# Copyright 2017 Guenter Bartsch
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import logging
import subprocess
import tempfile

class ESpeakNG(object):

    def __init__(self, 
                 volume      =         100, 
                 audio_dev   =        None,
                 word_gap    =          -1, # ms
                 capitals    =           0, # indicate capital letters with: 1=sound, 2=the word "capitals", higher values indicate a pitch increase (try -k20).
                 line_length =           0, # Line length. If not zero, consider lines less than this length as end-of-clause
                 pitch       =          50, # 0-99
                 speed       =         175, # approx. words per minute 
                 voice       = 'english-us'):


        self._volume      = volume  
        self._audio_dev   = audio_dev  
        self._word_gap    = word_gap   
        self._capitals    = capitals   
        self._line_length = line_length
        self._pitch       = pitch      
        self._speed       = speed      
        self._voice       = voice      

    def _espeak_exe(self, args, sync=False):
        cmd = ['espeak-ng', 
               '-a', str(self._volume),
               '-k', str(self._capitals), 
               '-l', str(self._line_length), 
               '-p', str(self._pitch), 
               '-s', str(self._speed), 
               '-v', self._voice, 
               '-b', '1', # UTF8 text encoding 
               ]

        if self._word_gap>=0:
            cmd.extend(['-g', str(self._word_gap)])

        cmd.extend(args)

        logging.debug('espeakng: executing %s' % repr(cmd))

        # '-w', f.name, s

        p = subprocess.Popen(cmd,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)

        res = iter(p.stdout.readline, b'')
        if not sync:
            p.stdout.close()
            if p.stderr:
                p.stderr.close()
            if p.stdin:
                p.stdin.close()
            return res

        res2 = []
        for line in res:
            res2.append(line)

        p.stdout.close()
        if p.stderr:
            p.stderr.close()
        if p.stdin:
            p.stdin.close()
        p.wait()

        return res2

    def say(self, txt, sync=False):

        txte = txt.encode('utf8')

        args = []

        if self._audio_dev:
            args.extend(['-d', self._audio_dev])

        args.append(txte)

        return self._espeak_exe(args, sync=sync)

    def synth_wav(self, txt, fmt='txt'):

        wav = None

        with tempfile.NamedTemporaryFile() as f:


            if fmt == 'xs':
                txt = '[[' + txt + ']]'
            elif fmt != 'txt':
                raise Exception ('unknown format: %s' % fmt)

            txte = txt.encode('utf8')

            args = ['-w', f.name, txte]

            self._espeak_exe(args, sync=True)

            f.seek(0)
            wav = f.read()

            logging.debug('read %s, got %d bytes.' % (f.name, len(wav)))

        return wav

    def g2p(self, txt, ipa=None, tie=None):

        args = ['-q']

        if ipa:
            args.append('--ipa=%s' % ipa)
        else:
            args.append('-x')
        
        if tie:
            args.append('--tie=%s' % tie)

        args.append(txt)

        phonemes = u''

        for line in self._espeak_exe(args, sync=True):

            logging.debug(u'line: %s' % repr(line))
            
            phonemes += line.decode('utf8').strip()

        return phonemes

    @property
    def voices(self):

        res = self._espeak_exe(['--voices'], sync=True)

        logging.debug ('espeakng: voices: %s' % res)

        # ['Pty', 'Language', 'Age/Gender', 'VoiceName', 'File', 'Other', 'Languages']

        voices = []

        first = True
        for v in res:
            if first:
                first=False
                continue
            parts = v.decode('utf8').split()

            if len(parts)<5:
                continue

            age_parts = parts[2].split('/')
            if len(age_parts) != 2:
                continue

            voice = {
                        'pty'        : parts[0],
                        'language'   : parts[1],
                        'age'        : age_parts[0],
                        'gender'     : age_parts[1],
                        'voice_name' : parts[3],
                        'file'       : parts[4],
                    }

            logging.debug ('espeakng: voices: parts= %s %s -> %s' % (len(parts), repr(parts), repr(voice)))
            voices.append(voice)

        return voices

    @property
    def volume(self):
        return self._volume
    @volume.setter
    def volume(self, v):
        self._volume = v

    @property
    def audio_dev(self):
        return self._audio_dev  
    @audio_dev.setter
    def audio_dev(self, v):
        self._audio_dev   = v

    @property
    def word_gap(self):
        return self._word_gap
    @word_gap.setter
    def word_gap(self, v):
        self._word_gap    = v

    @property
    def capitals(self):
        return self._capitals
    @capitals.setter
    def capitals(self, v):
        self._capitals    = v

    @property
    def line_length(self):
        return self._line_length
    @line_length.setter
    def line_length(self, v):
        self._line_length = v

    @property
    def pitch(self):
        return self._pitch
    @pitch.setter
    def pitch(self, v):
        self._pitch = v

    @property
    def speed(self):
        return self._speed
    @speed.setter
    def speed(self, v):
        self._speed = v

    @property
    def voice(self):
        return self._voice
    @voice.setter
    def voice(self, v):
        self._voice = v

    @property
    def samplerate(self):
        return self._samplerate
