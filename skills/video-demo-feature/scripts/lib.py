"""Helpers for driving the iOS Simulator with agent-device while recording a demo video.

Import from a flow script that lives next to this file (or add this folder to sys.path):

    import lib
    with lib.recording():
        lib.mark("Open the product")
        lib.tap("Gibson Home", "button")

Config (environment variables, all optional):
    DEMO_DIR        where raw.mp4, marks.tsv, start/end epochs are written (default: ./demo-out)
    SIM_UDID        simulator to record and drive (default: the booted "iPhone 16e")
    APP_DIR         directory agent-device is run from (default: <repo>/apps/mobile)
    DEMO_NO_RECORD  set to 1 for a dry run: same steps, no recording, marks are only printed
"""
import contextlib
import glob
import os
import re
import signal
import subprocess
import time

DEMO_DIR = os.path.abspath(os.environ.get('DEMO_DIR', 'demo-out'))
os.makedirs(DEMO_DIR, exist_ok=True)
DRY_RUN = os.environ.get('DEMO_NO_RECORD') == '1'


def _repo_root():
    return subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True).stdout.strip()


# agent-device sessions are keyed by the directory it is run from. A session opened from another
# directory holds the device and every later call fails with DEVICE_IN_USE, so always use this one.
APP_DIR = os.environ.get('APP_DIR') or os.path.join(_repo_root(), 'apps', 'mobile')

ENV = dict(os.environ)
_nvm_bins = sorted(glob.glob(os.path.expanduser('~/.nvm/versions/node/*/bin')))
if _nvm_bins:
    ENV['PATH'] = _nvm_bins[-1] + ':' + ENV['PATH']


def _booted_udid(name='iPhone 16e'):
    out = subprocess.run(['xcrun', 'simctl', 'list', 'devices', 'booted'], capture_output=True, text=True).stdout
    m = re.search(re.escape(name) + r' \(([0-9A-F-]{36})\) \(Booted\)', out)
    if not m:
        raise SystemExit(f'{name} is not booted. Boot it first: xcrun simctl boot "{name}"')
    return m.group(1)


UDID = os.environ.get('SIM_UDID') or _booted_udid()
NODE = re.compile(r'^\s*@(e\d+) \[([^\]]+)\](?: "(.*?)")?(.*)$')


# ---------------------------------------------------------------- simulator state
def set_location(lat, lon):
    """Fake the device location. The app is US-only, so use a US point (Apple Park: 37.3349, -122.0090)."""
    subprocess.run(['xcrun', 'simctl', 'location', UDID, 'set', f'{lat},{lon}'], check=True)


def reset_permission(service, bundle):
    """e.g. reset_permission('location', 'mobile.shopit.store') so the system prompt shows again."""
    subprocess.run(['xcrun', 'simctl', 'privacy', UDID, 'reset', service, bundle], check=True)


# ---------------------------------------------------------------- agent-device
def ad(*args):
    p = subprocess.run(['agent-device', *args], cwd=APP_DIR, env=ENV, capture_output=True, text=True)
    return p.stdout + p.stderr


def snap():
    """Interactive accessibility snapshot as a list of {ref, kind, label, rest}. Refs shift on every
    screen change (the keyboard appearing renumbers everything), so never reuse one across steps."""
    nodes = []
    for line in ad('snapshot', '-i', '--platform', 'ios').splitlines():
        m = NODE.match(line)
        if m:
            nodes.append({'ref': '@' + m.group(1), 'kind': m.group(2), 'label': m.group(3) or '', 'rest': m.group(4)})
    return nodes


def find(nodes, label, kind=None, exact=False, enabled=True):
    for n in nodes:
        if kind and n['kind'] != kind:
            continue
        if enabled and '[disabled]' in n['rest']:
            continue
        if (n['label'] == label) if exact else (label.lower() in n['label'].lower()):
            return n
    return None


def wait_for(label, kind=None, timeout=25, exact=False):
    end = time.time() + timeout
    while time.time() < end:
        n = find(snap(), label, kind, exact)
        if n:
            return n
        time.sleep(0.8)
    raise SystemExit(f'TIMEOUT waiting for {label!r}')


def tap(label, kind=None, timeout=25, exact=False):
    """Re-reads the screen, presses the match, retries once if the tap did not register.
    Elements reported as kind 'other' (e.g. 'Save & Continue', 'Add to Cart') are pressable too."""
    n = wait_for(label, kind, timeout, exact)
    out = ad('press', n['ref'])
    if 'Tapped' not in out:
        time.sleep(1)
        n = wait_for(label, kind, 10, exact)
        out = ad('press', n['ref'])
    print('  tap', label, '->', out.strip().splitlines()[0][:60])


def fill(label, text, kind='text-field', timeout=25):
    """Focus first, then fill; a fill straight after a screen change often fails with 'no text input'."""
    for _ in range(4):
        n = wait_for(label, kind, timeout)
        ad('press', n['ref'])
        time.sleep(0.8)
        n = wait_for(label, kind, timeout)
        out = ad('fill', n['ref'], text)
        print('  fill', label, '->', out.strip().splitlines()[0][:40])
        if 'Filled' in out:
            return
        time.sleep(1.2)
    raise SystemExit(f'could not fill {label!r}')


def fill_unlabeled(index, text):
    """For fields with no accessibility label. Once a field holds text it gains a label (its value),
    so after filling field 0 the next empty field is index 0 again, not 1."""
    end = time.time() + 20
    while time.time() < end:
        fields = [n for n in snap() if n['kind'] == 'text-field' and not n['label']]
        if len(fields) > index:
            print('  fill field', index, '->', ad('fill', fields[index]['ref'], text).strip().splitlines()[0][:40])
            return
        time.sleep(0.8)
    raise SystemExit(f'TIMEOUT waiting for unlabeled field {index}')


def sign_out():
    """Home -> profile -> settings -> Sign out -> confirm. Leaves the app on a signed-out Home."""
    tap('Open profile', 'button')
    time.sleep(2)
    tap('Open settings', 'button')
    time.sleep(2)
    tap('Sign out', 'button', exact=True)
    time.sleep(2)
    tap('Sign Out', 'button', exact=True)
    time.sleep(4)
    if not find(snap(), 'Sign in', 'button'):
        raise SystemExit('still signed in after sign_out()')


# ---------------------------------------------------------------- recording and marks
def _p(name):
    return os.path.join(DEMO_DIR, name)


def mark(text):
    """Log what is about to happen. Marks are written BEFORE the action (a snapshot takes 1-5 s), and
    the wall clock they use drifts from the video timeline, so use them as an action log only. Caption
    timing must come from the video itself (see review.py)."""
    if DRY_RUN:
        print('[dry]', text)
        return
    t = time.time() - float(open(_p('start.epoch')).read())
    open(_p('marks.tsv'), 'a').write(f'{t:.2f}\t{text}\n')
    print(f'[{int(t // 60):02d}:{t % 60:05.2f}] {text}')


@contextlib.contextmanager
def recording():
    """Record the simulator to raw.mp4. Always stops the recorder, even when a step raises, so a
    failed run leaves a complete file to inspect (delete it before the next take)."""
    if DRY_RUN:
        yield
        return
    for f in ('raw.mp4', 'marks.tsv', 'start.epoch', 'end.epoch', 'rec.log'):
        with contextlib.suppress(FileNotFoundError):
            os.remove(_p(f))
    log = open(_p('rec.log'), 'w')
    proc = subprocess.Popen(
        ['xcrun', 'simctl', 'io', UDID, 'recordVideo', '--codec', 'h264', '--force', _p('raw.mp4')],
        stdout=log, stderr=log)
    for _ in range(60):
        if 'Recording started' in open(_p('rec.log')).read():
            break
        time.sleep(0.1)
    open(_p('start.epoch'), 'w').write(str(time.time()))
    try:
        yield
    finally:
        open(_p('end.epoch'), 'w').write(str(time.time()))
        proc.send_signal(signal.SIGINT)
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=20)
        print('recorded', _p('raw.mp4'), os.path.getsize(_p('raw.mp4')) // 1024, 'KB')
