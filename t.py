# pip install pydub
# Cần cài ffmpeg và có trong PATH (Windows/Mac/Linux)

from pydub import AudioSegment
from pathlib import Path

def mp3_to_wav(
    mp3_path: str,
    wav_path: str | None = None,
    sample_rate: int = 16000,
    mono: bool = True,
    normalize: bool = False,
):
    mp3_path = Path(mp3_path)
    if wav_path is None:
        wav_path = mp3_path.with_suffix(".wav")
    else:
        wav_path = Path(wav_path)

    audio = AudioSegment.from_file(mp3_path, format="mp3")

    if mono:
        audio = audio.set_channels(1)
    # WAV 16-bit PCM
    audio = audio.set_frame_rate(sample_rate).set_sample_width(2)

    if normalize:
        # chuẩn hoá mức âm (đưa peak về -1 dBFS)
        change = -1.0 - audio.max_dBFS
        audio = audio.apply_gain(change)

    audio.export(wav_path, format="wav")
    return str(wav_path)

# Ví dụ:
out = mp3_to_wav("phongthuymusic.mp3", sample_rate=16000, mono=True)
print(out)
