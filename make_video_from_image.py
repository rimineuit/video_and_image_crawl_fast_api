
# Down load image
import os
import wave
import contextlib
from natsort import natsorted
from moviepy import AudioFileClip, TextClip, ColorClip, ImageClip, CompositeVideoClip, vfx, afx

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
    
if __name__ == "__main__":
    import sys
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