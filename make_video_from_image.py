
# Down load image
import os
import gdown

def download_folder_and_rename(id: str, img_dir='./image'):
    gdown.download_folder(id=id)
    def rename_file_in_folder(img_dir=img_dir):
        for f in os.listdir(img_dir):
            os.rename(os.path.join(img_dir, f), os.path.join(img_dir, f"{f}.png"))
    
    rename_file_in_folder(img_dir)
    
    
# Lưu scripts
def save_scripts_to_folder(scripts: list[str], output_folder='./script'):
    os.mkdir(output_folder)
    for i, s in enumerate(scripts):
        # Tạo và ghi vào file 
        file_path = os.path.join(output_folder, f"{i+1}.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(s)

# Convert script to audio
from google import genai
from google.genai import types
import wave
from typing import List
def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
   with wave.open(filename, "wb") as wf:
      wf.setnchannels(channels)
      wf.setsampwidth(sample_width)
      wf.setframerate(rate)
      wf.writeframes(pcm)

def make_audio_from_script(script_dir='./script', api_key='AIzaSyAUeYtTRNafF4geV_eoO7JimqkLCcHhokU', voice_name='Sulafat', audio_dir='./audio'):
    os.mkdir(audio_dir)
    for f in natsort(os.listdir(script_dir)):
        with open(os.path.join(script_dir, f), 'r', encoding='utf-8') as file:
            script = file.read()
        
        prompt = f"""TTS this script:{script}"""
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=voice_name,
                    )
                )
            ),
        )
        )
        data = response.candidates[0].content.parts[0].inline_data.data
        file_name=f'{f[:-4]}.wav'
        wave_file(os.path.join(audio_dir, file_name), data) # Saves the file to current directory
    
# Tạo video
from moviepy import *
import numpy as np
import contextlib
from natsort import natsorted

def make_video(script_dir='./script', audio_dir='./audio', image_dir='./image', fps=30):
    output_video = os.path.join(audio_dir,'my_video.mp4')
    font = "Roboto-SemiBold.ttf"
    output_wav = os.path.join(audio_dir,'output.wav')
    """Nối list audio thành một audio duy nhất"""
    def merge_audio(audio_dir=audio_dir, silence=0.5, ouput_wav=output_wav):
    # Danh sách các file wav
        wav_files = natsorted(
    [os.path.join(audio_dir, f) for f in os.listdir(audio_dir) if f.endswith('.wav')]
)
        # Load âm thanh
        with wave.open(ouput_wav, "wb") as out:
            # lấy thông số từ file đầu tiên
            with wave.open(wav_files[0], "rb") as w:
                params = w.getparams()
                out.setparams(params)

            nchannels, sampwidth, framerate, _, _, _ = params

            # tạo 0.5 giây silence (byte array toàn 0)
            silence_frames = b"\x00" * int(framerate * nchannels * sampwidth * 0.5)

            # nối file + thêm silence
            for i, f in enumerate(wav_files):
                with wave.open(f, "rb") as w:
                    out.writeframes(w.readframes(w.getnframes()))
                # không thêm silence sau file cuối
                if i < len(wav_files) - 1:
                    out.writeframes(silence_frames)
                
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
    
    durations = get_durations(audio_dir)
    
    merge_audio()
    
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
            # final_clips.append(bg)
            # final_clips.append(script)  

            tmp+=durations[i]+0.5   
        else:
            img = img_clip[i].with_start(tmp).with_duration(durations[i]+0.5).with_effects(
        [vfx.FadeIn(1), vfx.FadeOut(1), afx.AudioFadeIn(1), afx.AudioFadeOut(1)]
        ).resized(lambda t: 1 + 0.02 * t).with_position(("center", "center"))
            script = script_clip[i].with_start(tmp).with_duration(durations[i]+0.5).with_effects([vfx.CrossFadeIn(0.5), vfx.CrossFadeOut(0.5)]).with_position(("center", "center"))
            bg = bg_clips[i].with_start(tmp).with_duration(durations[i]+0.5).with_effects([vfx.CrossFadeIn(0.5), vfx.CrossFadeOut(0.5)]).with_position(("center", "center"))
            final_clips.append(img)
            # final_clips.append(bg)
            # final_clips.append(script)

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

def main(id_folder, list_scripts, fps):
    # delete_resource()
    # download_folder_and_rename(id_folder)
    # save_scripts_to_folder(list_scripts)
    # make_audio_from_script()
    make_video(fps=fps)
    
import json
import sys
if __name__ == "__main__":
    # id = '1Cpb31dJSmGcrCnt7hdz3HW4wxFJvw2uS'
    # list_scripts = ['Xin chào các bạn! Hôm nay chúng ta sẽ khám phá về Ngũ Hành, nền tảng của phong thủy phương Đông. Đó là Kim, Mộc, Thủy, Hỏa, Thổ',
    #                 'Hành Kim tượng trưng cho kim loại, mang tính chất thu lại, đại diện cho sự sắc bén, mạnh mẽ và công lý.',
    #                 'Hành Mộc là cây cối, biểu thị sự sinh trưởng, khởi đầu mới, năng động và dẻo dai.',
    #                 'Hành Thủy là nước, tượng trưng cho sự uyển chuyển, linh hoạt, tàng chứa và dòng chảy không ngừng.',
    #                 'Hành Hỏa đại diện cho lửa, sức mạnh, nhiệt huyết và sự bùng cháy đam mê, mang lại ánh sáng.',
    #                 'Cuối cùng, Hành Thổ là đất, tượng trưng cho sự ổn định, nuôi dưỡng và là nền tảng vững chắc cho vạn vật.',
    #                 'Ngũ Hành có quy luật Tương Sinh: Mộc sinh Hỏa, Hỏa sinh Thổ, Thổ sinh Kim, Kim sinh Thủy, Thủy sinh Mộc. Tức là các hành hỗ trợ nhau phát triển.',
    #                 'Và quy luật Tương Khắc: Kim khắc Mộc, Mộc khắc Thổ, Thổ khắc Thủy, Thủy khắc Hỏa, Hỏa khắc Kim. Các hành này chế ngự lẫn nhau để duy trì cân bằng.',
    #                 'Việc hiểu Ngũ Hành giúp ta cân bằng năng lượng, ứng dụng vào màu sắc, hướng nhà để thu hút tài lộc, may mắn.',
    #                 'Hãy áp dụng phong thủy Ngũ Hành để kiến tạo không gian sống hài hòa, bình an và phát triển toàn diện nhé!']
    id = sys.argv[1]
    fps = int(sys.argv[2])
    list_scripts = json.loads(sys.argv[3])
    main(id, list_scripts, fps)