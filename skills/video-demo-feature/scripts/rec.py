#!/usr/bin/env python3
"""rec.py start | stop | mark "text"   (detached recorder so the drive can be done in short phases)"""
import os
import subprocess
import sys
import time

D = os.path.dirname(os.path.abspath(__file__))
U = os.environ.get('SIM_UDID', 'booted')  # set SIM_UDID, or 'booted' records the booted device


def p(n):
    return os.path.join(D, n)


cmd = sys.argv[1]
if cmd == 'start':
    log = open(p('rec.log'), 'w')
    pr = subprocess.Popen(['xcrun', 'simctl', 'io', U, 'recordVideo', '--codec', 'h264', '--force', p('raw.mp4')],
                          stdout=log, stderr=log, start_new_session=True)
    open(p('rec.pid'), 'w').write(str(pr.pid))
    for _ in range(60):
        if 'Recording started' in open(p('rec.log')).read():
            break
        time.sleep(0.1)
    open(p('start.epoch'), 'w').write(str(time.time()))
    print('recording started')
elif cmd == 'mark':
    t = time.time() - float(open(p('start.epoch')).read())
    open(p('marks.tsv'), 'a').write(f'{t:.2f}\t{sys.argv[2]}\n')
    print(f'[{t:6.1f}s] {sys.argv[2]}')
elif cmd == 'stop':
    open(p('end.epoch'), 'w').write(str(time.time()))
    subprocess.run(['kill', '-INT', open(p('rec.pid')).read()])
    time.sleep(4)
    print('stopped', os.path.getsize(p('raw.mp4')) // 1024, 'KB')
