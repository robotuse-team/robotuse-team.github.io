#!/usr/bin/env python3
"""Render the concept film from the public storyboard and native media.

Python 3.10+, Pillow, ffmpeg and ffprobe. No generated robot imagery or
interpolated physical motion. Message cards are editorial summaries of the
recorded language handoffs; source event references live in the storyboard.
"""
from __future__ import annotations
import argparse
from functools import lru_cache
import json
import math
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw, ImageFont
from render_handoff import digest, encoder, fit, font_path, read_exact, wrap

SIZE = (1920, 1080)
INK = '#151515'
BLUE = '#176bce'
TEAL = '#087a6f'
MUTED = '#606a75'
LINE = '#d5dde6'
WASH = '#eef5fc'
SCENE = (640, 190, 1856, 744)
CENTERS = {'main': 276, 'subagent': 960, 'backend': 1644}
LABELS = {'main': 'Main agent', 'subagent': 'Subagent', 'backend': 'Backend'}
ROLES = {'main': 'LANGUAGE', 'subagent': 'VISUAL', 'backend': 'EXECUTION'}
STATUSES = {'main': 'Task goal + returned reports', 'subagent': 'Point · gripper pose · pose edits', 'backend': 'Generate previews · execute · observe'}
INSTRUCTIONS = {
    'Request': 'Get an overhead view of both bowls.',
    'Point': 'Find the left bowl in the current view.',
    'Grasps': 'Grasp the left bowl for transport.',
    'Inspect': 'Grasp the left bowl for transport.',
    'Approach': 'Grasp the left bowl for transport.',
    'Lift': 'Grasp the left bowl for transport.',
    'Receiver': 'Find the receiving bowl on the table.',
    'Pose': 'Stack the held bowl inside the right bowl.',
    'Shift': 'Stack the held bowl inside the right bowl.',
    'Adjust': 'Stack the held bowl inside the right bowl.',
    'Place': 'Stack the held bowl inside the right bowl.',
    'Outcome': 'Stack the held bowl inside the right bowl.',
}


def ease(value):
    value = max(0, min(1, value))
    return value * value * (3 - 2 * value)


def rows(draw, text, font, width):
    return [line for paragraph in text.split('\n') for line in wrap(draw, paragraph, font, width)]


def text_block(draw, position, text, font, width, fill=INK, leading=1.23, limit=None):
    x, y = position
    lines = rows(draw, text, font, width)
    height = math.ceil(font.size * leading)
    if limit is not None and y + len(lines) * height > limit:
        raise ValueError(f'Text exceeds its panel: {text}')
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += height
    return y


def put_image(canvas, source, box):
    resized, position = fit(source, box)
    canvas.paste(resized, position)


class Film:
    def __init__(self, root, storyboard):
        self.root = root
        self.media = root / 'assets/media'
        self.storyboard = storyboard
        regular, bold = font_path(), font_path(True)
        self.fonts = {key: ImageFont.truetype(bold if weight else regular, size)
                      for key, size, weight in [('brand', 32, True), ('tiny', 19, False),
                      ('label', 23, True), ('title', 56, True), ('body', 31, False),
                      ('node', 30, True), ('status', 18, False), ('packet', 25, True),
                      ('packet_kind', 21, True), ('language', 33, True), ('hero', 76, True)]}
        self.direction_y = {}
        source = self.media / 'alin-bowl-source.mp4'
        metadata = json.loads(subprocess.check_output(['ffprobe', '-v', 'error',
            '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate',
            '-of', 'json', str(source)]))['streams'][0]
        w, h = metadata['width'], metadata['height']
        n, d = map(int, metadata['r_frame_rate'].split('/'))
        self.source_fps = n / d
        decoder = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', str(source),
            '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1'], stdout=subprocess.PIPE)
        self.frames = []
        while (raw := read_exact(decoder.stdout, w * h * 3)) is not None:
            self.frames.append(Image.frombytes('RGB', (w, h), raw))
        decoder.stdout.close()
        if decoder.wait() or not self.frames:
            raise RuntimeError('Simulator source did not decode')

    @lru_cache(maxsize=40)
    def image(self, name):
        return Image.open(self.media / name).convert('RGB')

    @lru_cache(maxsize=180)
    def motion(self, frame):
        return fit(self.frames[frame], SCENE)

    def background(self, segment, index):
        canvas = Image.new('RGB', SIZE, 'white')
        draw = ImageDraw.Draw(canvas)
        draw.rectangle((0, 0, 1920, 96), fill=INK)
        draw.text((64, 25), 'RobotUse', font=self.fonts['brand'], fill='white')
        draw.text((1330, 33), 'LANGUAGE–VISUAL HANDOFF', font=self.fonts['tiny'], fill='#d2e3f7')
        layout = segment['layout']
        if layout not in ('intro', 'outro', 'physical'):
            left_label = 'MAIN AGENT · LANGUAGE' if segment['flow'] == ['main', 'subagent'] else 'LANGUAGE → VISUAL HANDOFF'
            draw.text((64, 123), left_label, font=self.fonts['label'], fill=BLUE)
            y = text_block(draw, (64, 173), segment['title'], self.fonts['title'], 500, limit=451)
            self.direction_y[segment['id']] = y + 27
            draw.text((64, y + 27), segment.get('direction', ''), font=self.fonts['label'], fill=BLUE)
            text_block(draw, (64, y + 87), segment['body'], self.fonts['body'], 494, limit=616)
            draw.rounded_rectangle((64, 630, 564, 756), radius=9, fill=WASH, outline=LINE, width=2)
            draw.text((82, 643), 'MAIN AGENT · LANGUAGE', font=self.fonts['packet_kind'], fill=BLUE)
            text_block(draw, (82, 673), INSTRUCTIONS[segment['phase']], self.fonts['language'], 466, leading=1.08, limit=752)
            owner = segment['scene_owner']
            owner_color = MUTED if owner.startswith('Backend') else TEAL
            draw.text((640, 130), owner.upper(), font=self.fonts['label'], fill=owner_color)
            draw.rectangle(SCENE, fill='#f5f7fa', outline=LINE, width=2)
            if layout in ('still', 'candidates', 'revision'):
                put_image(canvas, self.image(segment['image']), SCENE)
            badge = segment.get('badge', 'Recorded simulator motion' if layout == 'motion' else 'Native visual evidence')
            draw.text((640, 752), badge, font=self.fonts['tiny'], fill=MUTED)
            if segment.get('inset'):
                draw.rectangle((1616, 181, 1836, 320), fill='white', outline=BLUE, width=3)
                put_image(canvas, self.image(segment['inset']), (1621, 186, 1831, 304))
        else:
            self.full_scene(canvas, segment)
        draw.text((64, 762), 'Condensed recorded handoffs', font=self.fonts['tiny'], fill=MUTED)
        return canvas

    def full_scene(self, canvas, segment):
        draw = ImageDraw.Draw(canvas)
        layout = segment['layout']
        if layout == 'intro':
            put_image(canvas, self.image('alin-target-focus.jpg'), (64, 140, 590, 725))
            put_image(canvas, self.image('alin-grasp-1.png'), (655, 140, 1181, 725))
            put_image(canvas, self.image('panda-stack-capture_0011.png'), (1246, 140, 1856, 725))
            region = (0, 96, 1920, 780)
            overlay = Image.new('RGB', (1920, 684), INK)
            canvas.paste(Image.blend(canvas.crop(region), overlay, .69), region)
            draw = ImageDraw.Draw(canvas)
            draw.text((64, 25), 'RobotUse', font=self.fonts['brand'], fill='white')
            text_block(draw, (100, 212), segment['title'], self.fonts['hero'], 1700, 'white', leading=1.16)
            draw.text((105, 584), segment['body'], font=self.fonts['body'], fill='#d3e4f9')
        elif layout == 'physical':
            text_block(draw, (64, 125), segment['title'], self.fonts['title'], 1800, limit=292)
            self.physical_pair(canvas, 0)
        else:
            draw.rectangle((64, 144, 1856, 748), fill=WASH)
            text_block(draw, (110, 221), segment['title'], self.fonts['hero'], 1640, leading=1.18)
            draw.text((116, 520), 'RobotUse', font=self.fonts['title'], fill=BLUE)
            draw.text((116, 614), 'Language → visual choice → robot action → returned report', font=self.fonts['body'], fill=MUTED)

    def physical_pair(self, canvas, progress):
        # All original observations remain discrete and in capture order.
        for prefix, count, box, label in [
                ('panda-pick', 12, (64, 305, 929, 716), 'Pick & place'),
                ('panda-stack', 11, (991, 305, 1856, 716), 'Stack cubes')]:
            capture = min(int(progress * count) + 1, count)
            put_image(canvas, self.image(f'{prefix}-capture_{capture:04d}.png'), box)
            draw = ImageDraw.Draw(canvas)
            draw.text((box[0], 735), label, font=self.fonts['label'], fill=INK)
        draw = ImageDraw.Draw(canvas)
        draw.text((991, 762), 'Sampled camera observations · agent-reported completion', font=self.fonts['tiny'], fill=MUTED)

    def packet(self, segment, local):
        second = segment.get('second_at')
        if second is not None and local >= second:
            return (segment['second_flow'], segment['second_kind'], segment['second_packet'],
                    local - second, segment.get('second_medium', 'command'),
                    segment.get('second_image', segment.get('packet_image')), segment.get('second_crop'))
        return (segment['flow'], segment['packet_kind'], segment['packet'], local,
                segment['packet_medium'], segment.get('packet_image'), segment.get('packet_crop'))

    def architecture(self, canvas, segment, local):
        draw = ImageDraw.Draw(canvas)
        flow, kind, message, elapsed, medium, image_name, crop = self.packet(segment, local)
        color = TEAL if medium == 'visual' else MUTED if medium == 'feedback' else BLUE
        # Message holds at the sender, moves once, then stays at the receiver.
        fraction = ease((elapsed - .45) / 1.25)
        active = flow[0] if fraction < .5 else flow[1]
        for node, center in CENTERS.items():
            box = (center - 212, 943, center + 212, 1057)
            draw.rounded_rectangle(box, radius=9, fill=WASH if node == active else '#f8fafc',
                outline=color if node == active else LINE, width=3 if node == active else 2)
            role_color = TEAL if node == 'subagent' else BLUE if node == 'main' else MUTED
            draw.text((box[0] + 20, 950), ROLES[node], font=self.fonts['packet_kind'], fill=role_color)
            draw.text((box[0] + 20, 978), LABELS[node], font=self.fonts['node'], fill=color if node == active else INK)
            draw.text((box[0] + 20, 1026), STATUSES[node], font=self.fonts['status'], fill=MUTED)
            draw.line([(center, 943), (center, 935)], fill=LINE, width=3)
        for a, b in [(276, 960), (960, 1644)]:
            draw.line([(a, 935), (b, 935)], fill=LINE, width=3)
        start, end = [CENTERS[node] for node in flow]
        draw.line([(start, 935), (end, 935)], fill=color, width=4)
        sign = 1 if end > start else -1
        draw.polygon([(end, 935), (end - sign * 14, 930), (end - sign * 14, 940)], fill=color)
        x = start + (end - start) * fraction
        box = (round(x - 260), 790, round(x + 260), 927)
        draw.rounded_rectangle((box[0] + 4, box[1] + 5, box[2] + 4, box[3] + 5), radius=11, fill='#e2e8ee')
        draw.rounded_rectangle(box, radius=11, fill=WASH if medium == 'language' else 'white', outline=color, width=3)
        offset = 18
        if image_name:
            source = self.image(image_name)
            if crop:
                source = source.crop(crop)
            put_image(canvas, source, (box[0] + 10, 800, box[0] + 212, 917))
            draw.line((box[0] + 218, 803, box[0] + 218, 914), fill=LINE, width=2)
            offset = 230
        kind_font = self.fonts['packet_kind']
        if draw.textlength(kind, font=kind_font) > 502 - offset:
            kind_font = ImageFont.truetype(font_path(True), 17)
        draw.text((box[0] + offset, 803), kind, font=kind_font, fill=color)
        text_block(draw, (box[0] + offset, 839), message, self.fonts['packet'],
            502 - offset, leading=1.08, limit=925)

    def frame(self, segment, base, local):
        canvas = base.copy()
        if segment['layout'] == 'motion':
            source_time = min(segment['source_start'] + local, segment['source_end'])
            index = min(round(source_time * self.source_fps), len(self.frames) - 1)
            resized, pos = self.motion(index)
            canvas.paste(resized, pos)
            if segment.get('inset'):
                draw = ImageDraw.Draw(canvas)
                draw.rectangle((1616, 181, 1836, 320), fill='white', outline=BLUE, width=3)
                put_image(canvas, self.image(segment['inset']), (1621, 186, 1831, 304))
        elif segment['layout'] == 'revision':
            steps = ['alin-place-draft.png', 'alin-place-shift.png', 'alin-place-final.png']
            step = min(int(local / segment['duration'] * 3), 2)
            put_image(canvas, self.image(steps[step]), SCENE)
            draw = ImageDraw.Draw(canvas)
            labels = ['Initial proposal', '+20 / −30 mm', 'Then +1 / −12 mm']
            draw.rectangle((660, 674, 1110, 734), fill='white', outline=TEAL, width=2)
            draw.text((680, 687), labels[step], font=self.fonts['body'], fill=TEAL)
        elif segment['layout'] == 'candidates' and local >= segment['second_at']:
            # The backend proposes candidates; the subagent selects the recorded pose.
            put_image(canvas, self.image('alin-grasp-1.png'), SCENE)
            draw = ImageDraw.Draw(canvas)
            draw.rectangle((640, 119, 1856, 163), fill='white')
            draw.text((640, 130), 'SUBAGENT · SELECTED VISUAL GRASP', font=self.fonts['label'], fill=TEAL)
            draw.rectangle((660, 674, 1150, 734), fill='white', outline=TEAL, width=2)
            draw.text((680, 687), 'Grasp 1 · opening 44 mm', font=self.fonts['body'], fill=TEAL)
        elif segment['layout'] == 'physical':
            self.physical_pair(canvas, local / segment['duration'])
        if segment.get('second_at') is not None and local >= segment['second_at']:
            draw = ImageDraw.Draw(canvas)
            y = self.direction_y[segment['id']]
            draw.rectangle((64, y, 564, y + 34), fill='white')
            flow = segment['second_flow']
            color = TEAL if segment['second_medium'] == 'visual' else MUTED
            draw.text((64, y), f'{LABELS[flow[0]]} → {LABELS[flow[1]]}', font=self.fonts['label'], fill=color)
        self.architecture(canvas, segment, local)
        return canvas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--review-dir', type=Path, help='Save representative frames for layout review')
    parser.add_argument('--review-only', action='store_true')
    args = parser.parse_args()
    storyboard_path = args.root / 'data/explainer.json'
    storyboard = json.loads(storyboard_path.read_text())
    timeline_path = args.root / storyboard['source_timeline']
    timeline = json.loads(timeline_path.read_text())
    case = next(case for case in timeline['cases'] if case['id'] == storyboard['case_id'])
    phases = {phase['short']: phase for phase in case['phases']}
    for segment in storyboard['segments']:
        phase = phases[segment['phase']]
        if segment.get('source_event_seq'):
            events = [entry['event_seq'] for entry in phase.get('language_handoff', {}).values() if isinstance(entry, dict)]
            if segment['source_event_seq'] not in events:
                raise ValueError(f'Event reference mismatch: {segment["id"]}')
    film = Film(args.root, storyboard)
    fps = storyboard['fps']
    output = args.root / 'assets/media/robotuse-explainer.mp4'
    poster = output.with_suffix('.jpg')
    if args.review_dir:
        args.review_dir.mkdir(parents=True, exist_ok=True)
    sink = None if args.review_only else encoder(output, SIZE, fps)
    previous = None
    count = 0
    try:
        for index, segment in enumerate(storyboard['segments']):
            base = film.background(segment, index)
            frames = round(segment['duration'] * fps)
            frame_indices = sorted({0, frames // 2, frames - 1}) if args.review_only else range(frames)
            for n in frame_indices:
                canvas = film.frame(segment, base, n / fps)
                # Brief editorial dissolves; no scene-motion interpolation.
                if previous is not None and n < 7:
                    canvas = Image.blend(previous, canvas, (n + 1) / 7)
                if n == frames // 2:
                    if args.review_dir:
                        canvas.save(args.review_dir / f'{index:02d}-{segment["id"]}.jpg', quality=93)
                    if segment['id'] == 'point' and not args.review_only:
                        canvas.save(poster, quality=94)
                if sink:
                    sink.stdin.write(canvas.tobytes())
                count += 1
                if n == frames - 1:
                    last = canvas
            previous = last
            print(f'{segment["id"]}: {frames / fps:.2f}s', flush=True)
    finally:
        if sink:
            sink.stdin.close()
    if sink and sink.wait():
        raise RuntimeError('Concept film encoding failed')
    if args.review_only:
        return
    manifest_path = args.root / 'data/media.json'
    manifest = json.loads(manifest_path.read_text())
    names = {output.name, poster.name}
    manifest['files'] = [entry for entry in manifest['files'] if entry['file'] not in names]
    for path in [output, poster]:
        entry = {'file': path.name, 'kind': 'concept_film' if path == output else 'poster',
            'bytes': path.stat().st_size, 'sha256': digest(path),
            'source_storyboard': 'data/explainer.json', 'source_storyboard_sha256': digest(storyboard_path),
            'source_timeline': storyboard['source_timeline'], 'source_timeline_sha256': digest(timeline_path),
            'representation': storyboard['representation']}
        if path == output:
            entry.update(width=SIZE[0], height=SIZE[1], fps=fps, duration_s=count / fps)
        manifest['files'].append(entry)
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'output': str(output), 'duration_s': count / fps, 'bytes': output.stat().st_size}))


if __name__ == '__main__':
    main()
