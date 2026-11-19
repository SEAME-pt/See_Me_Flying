"""
RTTTL (Nokia ringtone) strings to notes: frequency and length.

    name:d=4,o=5,b=100:8e,8f#,4g,8p,2a.,...

d, o, b: default duration (1 = whole note, 4 = quarter...), octave and tempo
(quarter notes per minute). Each note: [duration]letter[#][.][octave][.];
'p' is a pause. Pure stdlib, so it runs anywhere.
"""
import re
from dataclasses import dataclass

LETTERS = {'c': 0, 'd': 2, 'e': 4, 'f': 5, 'g': 7, 'a': 9, 'b': 11}
NOTE = re.compile(r'^(\d+)?([a-gp])(#?)(\.?)(\d)?(\.?)$')


@dataclass
class Note:
    midi: int | None      # None for a pause
    seconds: float

    @property
    def hz(self):
        return None if self.midi is None else 440.0 * 2 ** ((self.midi - 69) / 12)


def parse(text):
    """All the notes of an RTTTL string, in order."""
    try:
        _, header, body = text.strip().split(':')
    except ValueError:
        raise ValueError('RTTTL needs three parts separated by ":"') from None
    defaults = {'d': 4, 'o': 6, 'b': 63}
    for item in filter(None, (s.strip() for s in header.split(','))):
        key, value = item.split('=')
        defaults[key.strip().lower()] = int(value)
    whole = 4 * 60.0 / defaults['b']   # seconds per whole note
    notes = []
    for token in filter(None, (s.strip().lower() for s in body.split(','))):
        m = NOTE.match(token)
        if not m:
            raise ValueError(f'not an RTTTL note: {token!r}')
        duration, letter, sharp, dot1, octave, dot2 = m.groups()
        seconds = whole / int(duration or defaults['d'])
        if dot1 or dot2:
            seconds *= 1.5
        if letter == 'p':
            notes.append(Note(None, seconds))
            continue
        octave = int(octave) if octave else defaults['o']
        notes.append(Note(12 * (octave + 1) + LETTERS[letter] + (1 if sharp else 0), seconds))
    return notes


def first_phrase(notes):
    """Up to and including the first pause (all of it if there is none)."""
    for i, n in enumerate(notes):
        if n.midi is None:
            return notes[:i + 1]
    return notes


def name(midi):
    return ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'][midi % 12] + \
        str(midi // 12 - 1)
