import json
import subprocess
import wave
import textwrap
from pathlib import Path
import imageio_ffmpeg

root=Path(__file__).resolve().parents[1]
output=root/'artifacts'/'video'
timeline=json.loads((output/'timeline.json').read_text(encoding='utf-8'))
rate=48000
samples=int((timeline['duration']+1)*rate)
audio=bytearray(samples*2)
for scene in timeline['scenes']:
    with wave.open(scene['audio']) as voice:
        assert voice.getframerate()==rate and voice.getnchannels()==1 and voice.getsampwidth()==2
        frames=voice.readframes(voice.getnframes())
    offset=int((scene['start']+1)*rate)*2
    audio[offset:offset+len(frames)]=frames
with wave.open(str(output/'narration.wav'),'wb') as target:
    target.setnchannels(1);target.setsampwidth(2);target.setframerate(rate);target.writeframes(audio)

def stamp(seconds):
    milliseconds=int(seconds*1000)
    return f'{milliseconds//3600000:02}:{milliseconds//60000%60:02}:{milliseconds//1000%60:02},{milliseconds%1000:03}'
subtitles=[]
for scene in timeline['scenes']:
    words=scene['narration'].split()
    for offset in range(0,len(words),13):
        chunk=words[offset:offset+13]
        start=scene['start']+1+scene['duration']*offset/len(words)
        end=scene['start']+1+scene['duration']*(offset+len(chunk))/len(words)
        subtitles.append(f"{len(subtitles)+1}\n{stamp(start)} --> {stamp(end)}\n{textwrap.fill(' '.join(chunk),width=58)}\n")
(output/'atmos-walkthrough.srt').write_text('\n'.join(subtitles),encoding='utf-8')
(output/'narration-script.md').write_text('\n\n'.join(f"## {scene['title']}\n\n{scene['narration']}" for scene in timeline['scenes']),encoding='utf-8')
target=output/'atmos-project-walkthrough.mp4'
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','warning','-ss',str(timeline['trimStart']),
    '-i',timeline['videoPath'],'-i',str(output/'narration.wav'),'-t',str(timeline['duration']),
    '-c:v','libx264','-preset','fast','-crf','21','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k',
    '-movflags','+faststart',str(target)],check=True)
print(f'Video ready: {target} ({timeline["duration"]:.1f}s)')
