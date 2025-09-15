# from moviepy import ImageClip, concatenate_videoclips
# import os
# from google import genai
# from google.genai import types
# import wave

# def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
#    with wave.open(filename, "wb") as wf:
#       wf.setnchannels(channels)
#       wf.setsampwidth(sample_width)
#       wf.setframerate(rate)
#       wf.writeframes(pcm)
      
# for f in os.listdir('script'):
#     if f.endswith('.txt'):
#         # Đọc nội dung từ file script
#         with open(os.path.join('script', f), 'r', encoding='utf-8') as file:
#             script = file.read()

#         prompt = f"""TTS this script:{script}"""
#         client = genai.Client(api_key="AIzaSyAUeYtTRNafF4geV_eoO7JimqkLCcHhokU")

#         response = client.models.generate_content(
#         model="gemini-2.5-flash-preview-tts",
#         contents=prompt,
#         config=types.GenerateContentConfig(
#             response_modalities=["AUDIO"],
#             speech_config=types.SpeechConfig(
#                 voice_config=types.VoiceConfig(
#                     prebuilt_voice_config=types.PrebuiltVoiceConfig(
#                     voice_name='Sulafat',
#                     )
#                 )
#             ),
#         )
#         )
#         data = response.candidates[0].content.parts[0].inline_data.data
#         file_name=f'{f[:-4]}.wav'
#         wave_file(os.path.join('audio',file_name), data) # Saves the file to current directory
    
            
            
# import os
# import wave
# from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

# list_img_clip = []
# img_files = sorted([f for f in os.listdir('imgs') if f.endswith('.png')])
# audio_files = sorted([f for f in os.listdir('audio') if f.endswith('.wav')])
# scripts = []
# for f in os.listdir('script'):
#     if f.endswith('.txt'):
#         # Đọc nội dung từ file script
#         with open(os.path.join('script', f), 'r', encoding='utf-8') as file:
#             script = file.read()
#             scripts.append(script)
# prev_duration = 0
# subs = []
# for img_file, audio_file in zip(img_files, audio_files):
#     # Lấy duration từ file wav
#     with wave.open(os.path.join('audio', audio_file), 'rb') as wf:
#         frames = wf.getnframes()
#         rate = wf.getframerate()
#         duration = frames / float(rate)
#     subs.append(((prev_duration, prev_duration + duration), scripts[len(subs)]))
#     # Clip ảnh
#     clip = ImageClip(os.path.join('imgs', img_file), duration=duration)
    
#     # Ghép audio vào clip ảnh
#     audio = AudioFileClip(os.path.join('audio', audio_file))
#     clip = clip.set_audio(audio)
#     list_img_clip.append(clip)

# # Nối các clip lại
# final_clip = concatenate_videoclips(list_img_clip, method="compose")
# final_clip.write_videofile("my_video.mp4", fps=24)

from moviepy import *
import numpy as np
import os
import wave
import contextlib

imgs_dir = 'imgs'
audio_dir = 'audio'
script_dir = 'script'
output_video = 'my_video.mp4'

font = "Roboto-SemiBold.ttf"

# Danh sách các file wav
files = [os.path.join(audio_dir, f) for f in os.listdir(audio_dir) if f.endswith('.wav')]
# Load âm thanh
with wave.open("audio/output.wav", "wb") as out:
    # lấy thông số từ file đầu tiên
    with wave.open(files[0], "rb") as w:
        params = w.getparams()
        out.setparams(params)

    nchannels, sampwidth, framerate, _, _, _ = params

    # tạo 0.5 giây silence (byte array toàn 0)
    silence_frames = b"\x00" * int(framerate * nchannels * sampwidth * 0.5)

    # nối file + thêm silence
    for i, f in enumerate(files):
        with wave.open(f, "rb") as w:
            out.writeframes(w.readframes(w.getnframes()))
        # không thêm silence sau file cuối
        if i < len(files) - 1:
            out.writeframes(silence_frames)
            
durations = []

audio_clip = AudioFileClip("audio/output.wav")
for f in files:
    with contextlib.closing(wave.open(f, 'rb')) as w:
        frames = w.getnframes()
        rate = w.getframerate()
        duration = frames / float(rate)
        durations.append(duration)
print(durations)      
# Load script
script_clip = []
for i in os.listdir(script_dir):
    if i.endswith('.txt'):
        with open(os.path.join(script_dir, i), 'r', encoding='utf-8') as f:
            script = f.read()
    script_clip.append(TextClip(text=script, font=font, font_size=34,horizontal_align='center',vertical_align='center', color='white', text_align='center', method='caption', size=(700, None)))
    
# Load ảnh
img_clip = []
for i in os.listdir(imgs_dir):
    if i.endswith('.png'):
        img = ImageClip(os.path.join(imgs_dir, i))
        img_clip.append(img)
import math
from PIL import Image
import numpy


def zoom_in_effect(clip, zoom_ratio=0.04):
    def effect(get_frame, t):
        img = Image.fromarray(get_frame(t))
        base_size = img.size

        new_size = [
            math.ceil(img.size[0] * (1 + (zoom_ratio * t))),
            math.ceil(img.size[1] * (1 + (zoom_ratio * t)))
        ]

        # The new dimensions must be even.
        new_size[0] = new_size[0] + (new_size[0] % 2)
        new_size[1] = new_size[1] + (new_size[1] % 2)

        img = img.resize(new_size, Image.LANCZOS)

        x = math.ceil((new_size[0] - base_size[0]) / 2)
        y = math.ceil((new_size[1] - base_size[1]) / 2)

        img = img.crop([
            x, y, new_size[0] - x, new_size[1] - y
        ]).resize(base_size, Image.LANCZOS)

        result = numpy.array(img)
        img.close()

        return result

    return clip.transform(effect)
# Tạo video từ ảnh, âm thanh và script
final_clips = []
tmp = 0
for i in range(len(img_clip)):
    print(tmp)
    if i == 0:
        img = img_clip[i].with_start(0).with_duration(durations[i]+0.5).with_effects(
    [vfx.FadeIn(1), vfx.FadeOut(1), afx.AudioFadeIn(1), afx.AudioFadeOut(1)]
).resized(lambda t: 1.25 - 0.02 * t).with_position(("center", "center"))
        script = script_clip[i].with_start(0).with_duration(durations[i]+0.5).with_effects([vfx.CrossFadeIn(0.5), vfx.CrossFadeOut(0.5)]).with_position(("center", "center"))
        final_clips.append(img)
        final_clips.append(script)  
        tmp+=durations[i]+0.5
    else:
        img = img_clip[i].with_start(tmp).with_duration(durations[i]+0.5).with_effects(
    [vfx.FadeIn(1), vfx.FadeOut(1), afx.AudioFadeIn(1), afx.AudioFadeOut(1)]
    ).resized(lambda t: 1.25 - 0.02 * t).with_position(("center", "center"))
        script = script_clip[i].with_start(tmp).with_duration(durations[i]+0.5).with_effects([vfx.CrossFadeIn(0.5), vfx.CrossFadeOut(0.5)]).with_position(("center", "center"))
        final_clips.append(img)
        final_clips.append(script)
        tmp+=durations[i]+0.5
        
final_video = CompositeVideoClip(final_clips)
final_video = final_video.with_audio(audio_clip)
final_video.write_videofile(output_video, fps=60)