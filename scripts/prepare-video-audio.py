import json
import subprocess
import wave
from pathlib import Path
import imageio_ffmpeg

root = Path(__file__).resolve().parents[1]
output = root / 'artifacts' / 'video'
scenes = json.loads((root / 'scripts' / 'video-storyboard.json').read_text(encoding='utf-8'))
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
for scene in scenes:
    target = output / (scene['id'] + '-paced.wav')
    subprocess.run([ffmpeg, '-y', '-loglevel', 'error', '-i', str(output / (scene['id'] + '.wav')),
        '-filter:a', 'atempo=1.35', '-ar', '48000', '-ac', '1', str(target)], check=True)
    with wave.open(str(target)) as audio:
        scene['duration'] = audio.getnframes() / audio.getframerate()
    scene['audio'] = str(target)
(output / 'scenes.json').write_text(json.dumps(scenes, indent=2), encoding='utf-8')
print('Narration seconds:', round(sum(scene['duration'] for scene in scenes), 1))
