#!/usr/bin/env python3
"""Post-processing for a recorded demo. Run from anywhere; files live in $DEMO_DIR (default ./demo-out).

    review.py compress                 raw.mp4 -> demo.mp4 (small enough to upload)
    review.py info                     wall-clock vs video duration
    review.py scenes                   video times where the screen visibly changes
    review.py frames 12 40 64.5 ...    labelled montage of frames at those video times -> frames.png
    review.py finish segments.json     validate segments, write timestamps.txt and subtitles.srt

segments.json is a list of [start, end, "text"] on the VIDEO timeline, in seconds.
"""
import json
import os
import re
import subprocess
import sys

D = os.path.abspath(os.environ.get('DEMO_DIR', 'demo-out'))
P = lambda n: os.path.join(D, n)  # noqa: E731
WORDS_PER_SEC = 2.7  # Piper "Ryan" reads about this fast; leave headroom or lines overlap the next one


def run(*a):
    return subprocess.run(a, capture_output=True, text=True)


def duration(path):
    return float(run('ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path).stdout)


def compress():
    # raw.mp4 is ~1 MB/s of screen time (87 MB for 95 s). Halving the size and dropping audio gives ~1.6 MB.
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', P('raw.mp4'), '-vf', 'scale=586:-2', '-c:v', 'libx264',
                    '-crf', '27', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-an', '-movflags', '+faststart',
                    P('demo.mp4')], check=True)
    print(P('demo.mp4'), os.path.getsize(P('demo.mp4')) // 1024, 'KB', round(duration(P('demo.mp4')), 1), 's')


def info():
    wall = float(open(P('end.epoch')).read()) - float(open(P('start.epoch')).read())
    print(f'wall clock {wall:.1f}s, video {duration(P("demo.mp4")):.1f}s')


def scenes():
    # Times where the picture changes a lot. Compare these with the mark log to see which event is which.
    out = run('ffmpeg', '-hide_banner', '-i', P('demo.mp4'), '-vf', "select='gt(scene,0.12)',showinfo", '-an', '-f',
              'null', '-').stderr
    times = [float(t) for t in re.findall(r'pts_time:([0-9.]+)', out)]
    print(' '.join(f'{t:.1f}' for t in times))


def frames(times):
    from PIL import Image, ImageDraw
    tiles = []
    for t in times:
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', str(t), '-i', P('demo.mp4'), '-frames:v', '1',
                        '-vf', 'scale=170:-2', P('_f.png')], check=True)
        tiles.append((t, Image.open(P('_f.png')).copy()))
    cols = 8
    w, h = tiles[0][1].size
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * w, rows * (h + 14)), 'white')
    d = ImageDraw.Draw(sheet)
    for k, (t, im) in enumerate(tiles):
        x, y = (k % cols) * w, (k // cols) * (h + 14)
        sheet.paste(im, (x, y + 14))
        d.text((x + 4, y + 1), f't={t}', fill='black')
    sheet.save(P('frames.png'))
    os.remove(P('_f.png'))
    print(P('frames.png'))


def finish(path):
    segs = json.load(open(path))
    length = duration(P('demo.mp4'))
    problems = []
    for i, (a, b, text) in enumerate(segs):
        if b <= a or b > length + 0.5:
            problems.append(f'segment {i + 1}: bad range {a}-{b} (video is {length:.1f}s)')
        if i and a < segs[i - 1][1] - 0.01:
            problems.append(f'segment {i + 1}: starts before the previous one ends')
        need = len(text.split()) / WORDS_PER_SEC
        if need > (b - a):
            problems.append(f'segment {i + 1}: {len(text.split())} words need ~{need:.1f}s but only {b - a:.1f}s available')
    if problems:
        print('\n'.join(problems))
        sys.exit(1)
    mmss = lambda x: f'{int(x // 60):02d}:{x % 60:04.1f}'  # noqa: E731
    ts = lambda x: f'{int(x // 3600):02d}:{int(x % 3600 // 60):02d}:{x % 60:06.3f}'.replace('.', ',')  # noqa: E731
    open(P('timestamps.txt'), 'w').write(''.join(f'[{mmss(a)}-{mmss(b)}] {t}\n' for a, b, t in segs))
    open(P('subtitles.srt'), 'w').write(''.join(f'{i + 1}\n{ts(a)} --> {ts(b)}\n{t}\n\n' for i, (a, b, t) in enumerate(segs)))
    print('wrote', P('timestamps.txt'), 'and', P('subtitles.srt'), f'({len(segs)} segments)')


if __name__ == '__main__':
    cmd, args = (sys.argv[1] if len(sys.argv) > 1 else ''), sys.argv[2:]
    if cmd == 'compress':
        compress()
    elif cmd == 'info':
        info()
    elif cmd == 'scenes':
        scenes()
    elif cmd == 'frames' and args:
        frames([float(a) for a in args])
    elif cmd == 'finish' and args:
        finish(args[0])
    else:
        sys.exit(__doc__)
