"""Build one fast-start MP4 per gallery tile and camera from the original clips."""
import argparse
import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
GALLERY = ROOT / 'robodojo' / 'gallery'


def read_cases(name):
    body = (GALLERY / f'{name}.js').read_text(encoding='utf-8').split('=', 1)[1]
    return json.loads(re.sub(r',\s*]', ']', body.strip().rstrip(';')))


def clips():
    for case in read_cases('robolab'):
        for method in ('robotuse', 'pivot'):
            name = f"{case['clip']}-{method}"
            yield ROOT / 'assets/media/robolab-seed0' / f'{name}.mp4', f'{name}-external.mp4'
    for episode in read_cases('episodes'):
        for camera in episode['durationSecondsByCamera']:
            result = 'success' if episode['success'] else 'fail'
            name = f"episode_{episode['layout']:07d}_cam_{camera}_{result}.mp4"
            source = ROOT / 'robodojo/videos' / episode['policy'] / episode['task'] / name
            yield source, f"{episode['id']}-{camera}.mp4"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ffmpeg', default='ffmpeg')
    args = parser.parse_args()
    previews = GALLERY / 'previews'
    previews.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=previews) as staging:
        def encode(clip):
            source, name = clip
            output = Path(staging) / name
            # Encode only the part shown by the 4:3 tiles. Never duplicate frames
            # in lower-frame-rate RoboLab recordings to reach the preview cap.
            subprocess.run([args.ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
                            '-threads', '1', '-i', str(source), '-an', '-map_metadata', '-1',
                            '-vf', "crop=ih*4/3:ih,scale=320:240:flags=lanczos,setsar=1",
                            '-fpsmax', '15', '-c:v', 'libx264', '-threads', '2',
                            '-preset', 'medium', '-crf', '23', '-g', '24',
                            '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(output)],
                           check=True)
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(encode, clips()))
        for output in Path(staging).iterdir():
            output.replace(previews / output.name)


if __name__ == '__main__':
    main()
