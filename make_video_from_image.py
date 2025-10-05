
import os
import wave
import contextlib
from natsort import natsorted
from moviepy import AudioFileClip, TextClip, ColorClip, ImageClip, CompositeVideoClip, vfx, afx

from pydub import AudioSegment
from pathlib import Path
# Lưu transcripts
def save_transcripts_to_folder(transcripts: list[str], output_folder='./script'):
    os.makedirs(output_folder, exist_ok=True)
    for i, s in enumerate(transcripts):
        file_path = os.path.join(output_folder, f"{i+1}.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(s)

# Download wav files from URLs
import requests

def download_wavs_from_urls(wav_urls, audio_dir='./audio'):
    os.makedirs(audio_dir, exist_ok=True)
    for i, url in enumerate(wav_urls):
        file_name = os.path.join(audio_dir, f"{i+1}.wav")
        r = requests.get(url)
        with open(file_name, 'wb') as f:
            f.write(r.content)

# Download images from URLs
def download_images_from_urls(image_urls, image_dir='./image'):
    os.makedirs(image_dir, exist_ok=True)
    for i, url in enumerate(image_urls):
        file_name = os.path.join(image_dir, f"{i+1}.png")
        r = requests.get(url)
        with open(file_name, 'wb') as f:
            f.write(r.content)
    
# Tạo video
def make_video(script_dir='./script', audio_dir='./audio', image_dir='./image', fps=30, show_script=False):
    output_video = os.path.join(audio_dir,'my_video.mp4')
    font = "Roboto-SemiBold.ttf"
    output_wav = os.path.join(audio_dir,'output.wav')
    """Nối list audio thành một audio duy nhất"""
    def merge_audio(audio_dir=audio_dir, silence=0.5, ouput_wav=output_wav, bg_wav_path="bg.wav"):
        # Danh sách các file wav
        wav_files = natsorted([
            os.path.join(audio_dir, f) for f in os.listdir(audio_dir) if f.endswith('.wav')
        ])
        # Load âm thanh chính và nối lại
        with wave.open(wav_files[0], "rb") as w:
            params = w.getparams()
        nchannels, sampwidth, framerate, _, _, _ = params
        silence_frames = b"\x00" * int(framerate * nchannels * sampwidth * silence)
        # Gộp audio chính
        audio_data = b""
        for i, f in enumerate(wav_files):
            with wave.open(f, "rb") as w:
                audio_data += w.readframes(w.getnframes())
            if i < len(wav_files) - 1:
                audio_data += silence_frames

        # Nếu có bg_wav, mix vào nếu định dạng phù hợp
        if os.path.exists(bg_wav_path):
            import numpy as np
            try:
                with wave.open(bg_wav_path, "rb") as bg:
                    bg_params = bg.getparams()
                    bg_frames = bg.readframes(bg.getnframes())
                # So sánh định dạng
                if (bg_params.nchannels == nchannels and
                    bg_params.sampwidth == sampwidth and
                    bg_params.framerate == framerate):
                    # Chuyển về numpy array
                    main_audio = np.frombuffer(audio_data, dtype=np.int16)
                    bg_audio = np.frombuffer(bg_frames, dtype=np.int16)
                    # Nếu nhạc nền ngắn hơn, lặp lại cho đủ độ dài
                    if len(bg_audio) < len(main_audio):
                        repeat_times = int(np.ceil(len(main_audio) / len(bg_audio)))
                        bg_audio = np.tile(bg_audio, repeat_times)[:len(main_audio)]
                    else:
                        bg_audio = bg_audio[:len(main_audio)]
                    # Trộn: nhạc nền nhỏ hơn
                    mixed = main_audio + (bg_audio * 0.2).astype(np.int16)
                    mixed = np.clip(mixed, -32768, 32767).astype(np.int16)
                    out_data = mixed.tobytes()
                else:
                    # Định dạng không phù hợp, chỉ dùng audio chính
                    out_data = audio_data
            except Exception as e:
                # Nếu lỗi, chỉ dùng audio chính
                out_data = audio_data
        else:
            out_data = audio_data

        # Ghi ra file
        with wave.open(ouput_wav, "wb") as out:
            out.setparams(params)
            out.writeframes(out_data)
                
    """Lấy durations audio để chỉnh sửa video"""
    def get_durations(audio_dir):
        durations = []
        wav_files = natsorted([os.path.join(audio_dir, f) for f in os.listdir(audio_dir) if f.endswith('.wav')])
        for f in wav_files:
            with contextlib.closing(wave.open(f, 'rb')) as w:
                frames = w.getnframes()
                rate = w.getframerate()
                duration = frames / float(rate)
                durations.append(duration)  
    
        return durations

    def _parse_time_to_ms(t):
        """t: float/int giây, hoặc chuỗi 'mm:ss' / 'hh:mm:ss(.ms)'."""
        if isinstance(t, (int, float)):
            if t <= 0:
                raise ValueError("end_time phải > 0")
            return int(round(float(t) * 1000))
        if isinstance(t, str):
            s = t.strip()
            # nếu là số thuần, hiểu là giây
            try:
                return int(round(float(s) * 1000))
            except ValueError:
                pass
            parts = s.split(":")
            if not (1 <= len(parts) <= 3):
                raise ValueError("Định dạng thời gian không hợp lệ")
            parts = [float(p) for p in parts]  # giây/phút/giờ có thể .ms
            if len(parts) == 1:  # "ss(.ms)"
                sec = parts[0]
            elif len(parts) == 2:  # "mm:ss(.ms)"
                sec = parts[0] * 60 + parts[1]
            else:  # "hh:mm:ss(.ms)"
                sec = parts[0] * 3600 + parts[1] * 60 + parts[2]
            if sec <= 0:
                raise ValueError("end_time phải > 0")
            return int(round(sec * 1000))
        raise TypeError("end_time phải là số (giây) hoặc chuỗi thời gian")

    def cut_wav_from_start(input_wav: str, end_time, output_wav: str | None = None, clamp=True) -> str:
        """
        Cắt từ đầu file WAV tới mốc `end_time` và lưu.
        - end_time: float/int (giây) hoặc chuỗi 'mm:ss' / 'hh:mm:ss(.ms)'
        - clamp=True: nếu end_time > độ dài thật, sẽ cắt tới hết file (không lỗi)
        """
        in_path = Path(input_wav)
        if output_wav is None:
            output_wav = in_path.with_name(in_path.stem + f"_cut.wav")
        out_path = Path(output_wav)

        audio = AudioSegment.from_wav(in_path)
        end_ms = _parse_time_to_ms(end_time)

        if end_ms > len(audio):
            if clamp:
                end_ms = len(audio)
            else:
                raise ValueError(f"end_time ({end_ms} ms) vượt độ dài file ({len(audio)} ms)")

        clip = audio[:end_ms]
        clip.export(out_path, format="wav")
        return str(out_path)
    
        # cut_wav_from_start("input.wav", "01:23.250", "input_0_1m23s250.wav") # 1 phút 23.250 giây

    durations = get_durations(audio_dir)
    sum_durations = sum(durations) + len(durations)*0.5
    
    cut_wav_from_start("phongthuymusic.wav", sum_durations, "bg.wav")  
      
    merge_audio()

    # Xóa 1 file
    # Path("bg.wav").unlink(missing_ok=True)  # Python 3.8+: không lỗi nếu không tồn tại
    
    audio_clip = AudioFileClip(output_wav)
    # Load script
    script_clip = []
    bg_clips = []
    for i in natsorted(os.listdir(script_dir)):
        if i.endswith('.txt'):
            with open(os.path.join(script_dir, i), 'r', encoding='utf-8') as f:
                script = f.read()
                
        import textwrap

        wrapped_text = "\n".join(textwrap.wrap(script, width=30))
        txt = TextClip(text=wrapped_text, font=font, font_size=38, color='white', text_align='center', method='caption', size=(600, None), margin=(5,10))
        
        script_clip.append(txt)
        bg = ColorClip(size=txt.size, color=(0, 0, 0)).with_opacity(0.7)
        bg_clips.append(bg)
        
    # Load ảnh
    img_clip = []
    for i in natsorted(os.listdir(image_dir)):
        if i.endswith('.png'):
            img = ImageClip(os.path.join(image_dir, i))
            img_clip.append(img)
            
    # Tạo video từ ảnh, âm thanh và script
    final_clips = []
    tmp = 0
    for i in range(len(img_clip)):
        print(tmp)
        if i == 0:
            img = img_clip[i].with_start(0).with_duration(durations[i]+0.5).with_effects(
        [vfx.FadeIn(1), vfx.FadeOut(1), afx.AudioFadeIn(1), afx.AudioFadeOut(1)]
        ).resized(lambda t: 1 + 0.02 * t).with_position(("center", "center"))
            script = script_clip[i].with_start(0).with_duration(durations[i]+0.5).with_effects([vfx.CrossFadeIn(0.5), vfx.CrossFadeOut(0.5)]).with_position(("center", "center"))
            bg = bg_clips[i].with_start(0).with_duration(durations[i]+0.5).with_effects([vfx.CrossFadeIn(0.5), vfx.CrossFadeOut(0.5)]).with_position(("center", "center"))
            final_clips.append(img)
            if show_script:
                final_clips.append(bg)
                final_clips.append(script)  

            tmp+=durations[i]+0.5   
        else:
            img = img_clip[i].with_start(tmp).with_duration(durations[i]+0.5).with_effects(
        [vfx.FadeIn(1), vfx.FadeOut(1), afx.AudioFadeIn(1), afx.AudioFadeOut(1)]
        ).resized(lambda t: 1 + 0.02 * t).with_position(("center", "center"))
            script = script_clip[i].with_start(tmp).with_duration(durations[i]+0.5).with_effects([vfx.CrossFadeIn(0.5), vfx.CrossFadeOut(0.5)]).with_position(("center", "center"))
            bg = bg_clips[i].with_start(tmp).with_duration(durations[i]+0.5).with_effects([vfx.CrossFadeIn(0.5), vfx.CrossFadeOut(0.5)]).with_position(("center", "center"))
            final_clips.append(img)
            if show_script:
                final_clips.append(bg)
                final_clips.append(script) 

            tmp+=durations[i]+0.5
    
    final_video = CompositeVideoClip(final_clips)
    final_video = final_video.with_audio(audio_clip)
    final_video.write_videofile(output_video, fps=fps)

import shutil
def delete_resource(script_dir='./script', audio_dir='./audio', image_dir='./image'):
    if os.path.exists(script_dir) and os.path.isdir(script_dir):
        shutil.rmtree(script_dir)
    if os.path.exists(audio_dir) and os.path.isdir(audio_dir):
        shutil.rmtree(audio_dir)
    if os.path.exists(image_dir) and os.path.isdir(image_dir):
        shutil.rmtree(image_dir)

def main(transcripts, wav_urls, image_urls, fps=30, show_script=False):
    delete_resource()
    save_transcripts_to_folder(transcripts)
    download_wavs_from_urls(wav_urls)
    download_images_from_urls(image_urls)
    make_video(fps=fps, show_script=show_script)
    
import sys
if __name__ == "__main__":
    import json
    if len(sys.argv) < 6:
        print("Usage: python make_video_from_image.py <transcripts_json> <wav_urls_json> <image_urls_json> <fps> <show_script>")
        sys.exit(1)

    transcripts = json.loads(sys.argv[1])
    wav_urls = json.loads(sys.argv[2])
    image_urls = json.loads(sys.argv[3])
    fps = int(sys.argv[4])
    show_script = sys.argv[5].lower() in ("true", "1", "yes")

    main(transcripts, wav_urls, image_urls, fps=fps, show_script=show_script)