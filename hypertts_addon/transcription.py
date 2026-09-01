import base64
import html
import json
import re
from dataclasses import dataclass
from typing import List, Optional, Sequence


@dataclass
class TranscriptSegment:
    s: float
    e: float
    w: str


@dataclass
class TtsAudioTranscript:
    audio: bytes
    transcript_json: Optional[str] = None


@dataclass
class SsmlMarkedText:
    ssml: str
    words: List[str]


def serialize_segments(segments: List[TranscriptSegment]) -> str:
    """Serialize transcript segments for Anki fields.

    Example: serialize_segments([TranscriptSegment(0, 0.2, 'hello')])
    """
    return json.dumps(
        [{'s': segment.s, 'e': segment.e, 'w': segment.w} for segment in segments],
        ensure_ascii=False,
        separators=(',', ':'),
    )


def decode_elevenlabs_audio(response_data) -> bytes:
    """Decode ElevenLabs timestamp response audio.

    Example: decode_elevenlabs_audio({'audio_base64': '...'})
    """
    encoded = response_data.get('audio_base64')
    if not encoded:
        raise ValueError(f"audio_base64 missing in ElevenLabs response {response_data}; expected response with audio_base64")
    return base64.b64decode(encoded)


def elevenlabs_alignment_to_segments(response_data) -> List[TranscriptSegment]:
    """Convert ElevenLabs character alignment to word segments.

    Example: elevenlabs_alignment_to_segments({'alignment': {...}})
    """
    alignment = response_data.get('normalized_alignment') or response_data.get('alignment')
    if not alignment:
        raise ValueError(f"alignment missing in ElevenLabs response {response_data}; expected alignment or normalized_alignment")
    characters = alignment['characters']
    starts = alignment['character_start_times_seconds']
    ends = alignment['character_end_times_seconds']
    return character_alignment_to_segments(characters, starts, ends)


def character_alignment_to_segments(characters: Sequence[str], starts: Sequence[float], ends: Sequence[float]) -> List[TranscriptSegment]:
    """Group character timestamps into word segments.

    Example: character_alignment_to_segments(['h', 'i'], [0, 0.1], [0.1, 0.2])
    """
    segments = []
    word_chars = []
    word_start = None
    word_end = None
    for index, character in enumerate(characters):
        if character.isspace():
            _append_segment(segments, word_chars, word_start, word_end)
            word_chars = []
            word_start = None
            word_end = None
            continue
        if word_start is None:
            word_start = starts[index]
        word_end = ends[index]
        word_chars.append(character)
    _append_segment(segments, word_chars, word_start, word_end)
    return segments


def _append_segment(segments, word_chars, word_start, word_end):
    if not word_chars:
        return
    segments.append(TranscriptSegment(round(word_start, 3), round(word_end, 3), ''.join(word_chars)))


def build_marked_ssml(source_text: str) -> SsmlMarkedText:
    """Build SSML marks before each word and at the end.

    Example: build_marked_ssml('hello world')
    """
    words = re.findall(r'\S+', source_text)
    if not words:
        raise ValueError(f"source_text has no words for SSML marks: {source_text!r}; expected non-empty text")
    marked_words = []
    for index, word in enumerate(words):
        marked_words.append(f'<mark name="w{index}"/>{html.escape(word)}')
    marked_words.append(f'<mark name="w{len(words)}"/>')
    return SsmlMarkedText(f"<speak>{' '.join(marked_words)}</speak>", words)


def google_timepoints_to_segments(words, timepoints) -> List[TranscriptSegment]:
    """Convert Google SSML mark timepoints to word segments.

    Example: google_timepoints_to_segments(['hello'], [{'markName': 'w0', 'timeSeconds': 0}, {'markName': 'w1', 'timeSeconds': 0.2}])
    """
    time_by_mark = {timepoint['markName']: timepoint['timeSeconds'] for timepoint in timepoints}
    segments = []
    for index, word in enumerate(words):
        start_mark = f'w{index}'
        end_mark = f'w{index + 1}'
        if start_mark not in time_by_mark or end_mark not in time_by_mark:
            raise ValueError(f"missing Google timepoint marks for word {word!r}: {timepoints}; expected marks {start_mark} and {end_mark}")
        segments.append(TranscriptSegment(round(time_by_mark[start_mark], 3), round(time_by_mark[end_mark], 3), word))
    return segments
