"""Helpers for driving the iOS Simulator with agent-device while recording a demo video.

Import from a flow script that lives next to this file (or add this folder to sys.path):

    import lib
    with lib.recording():
        lib.mark("Open the product")
        lib.tap("Gibson Home", "button")

Config (environment variables, all optional):
    DEMO_DIR        where raw.mp4, marks.tsv, start/end epochs are written (default: ./demo-out)
    SIM_UDID        simulator to record and drive (default: the booted "iPhone 16e")
    APP_DIR         directory agent-device is run from (default: apps/mobile found above the cwd)
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


def _find_app_dir():
    # Walk up from the current directory to the folder holding apps/mobile. Do not use
    # `git rev-parse`: .claude/ is a nested git repo, so from a skill script it returns .claude.
    # Try the current directory first, then this file's own location (the skill lives inside the repo,
    # so this still works when the flow script is run from a scratch directory outside it).
    for start in (os.getcwd(), os.path.dirname(os.path.abspath(__file__))):
        d = start
        while d != os.path.dirname(d):
            if os.path.isdir(os.path.join(d, 'apps', 'mobile')):
                return os.path.join(d, 'apps', 'mobile')
            d = os.path.dirname(d)
    raise SystemExit('Could not find apps/mobile above the current directory; set APP_DIR')


# agent-device sessions are keyed by the directory it is run from. A session opened from another
# directory holds the device and every later call fails with DEVICE_IN_USE, so always use this one.
APP_DIR = os.environ.get('APP_DIR') or _find_app_dir()

ENV = dict(os.environ)
# Put the NVM node that actually has agent-device first (several node versions are installed and it
# lives under only one of them), then the rest, so `node` is found too.
_nvm_bins = sorted(glob.glob(os.path.expanduser('~/.nvm/versions/node/*/bin')))
_with_tool = [b for b in _nvm_bins if os.path.exists(os.path.join(b, 'agent-device'))]
ENV['PATH'] = ':'.join(_with_tool + [b for b in _nvm_bins if b not in _with_tool] + [ENV['PATH']])


def _booted_udid(name='iPhone 16e'):
    out = subprocess.run(['xcrun', 'simctl', 'list', 'devices', 'booted'], capture_output=True, text=True).stdout
    m = re.search(re.escape(name) + r' \(([0-9A-F-]{36})\) \(Booted\)', out)
    if not m:
        raise SystemExit(f'{name} is not booted. Boot it first: xcrun simctl boot "{name}"')
    return m.group(1)


def ensure_headful():
    """Never drive or record a headless simulator: it hides the QWERTY keyboard until text is typed, so
    keyboard checks and recordings mislead. The window host is DeviceHub on Xcode 27 (Simulator.app on
    older Xcode). Open it, or stop and tell the user."""
    hosts = ('DeviceHub', 'Simulator')

    def running():
        return any(subprocess.run(['pgrep', '-x', h], capture_output=True).returncode == 0 for h in hosts)
    if running():
        return
    for cmd in (['open', '-b', 'com.apple.dt.Devices'], ['open', '-a', 'Simulator']):
        subprocess.run(cmd, capture_output=True)
        for _ in range(10):
            if running():
                return
            time.sleep(0.5)
    raise SystemExit('Neither DeviceHub nor Simulator could be opened, so the simulator would be headless. '
                     'Stop and tell the user; do not continue or record headless.')


ensure_headful()
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
    """Fill directly, retrying after a pause ("no text input found" is common while a screen or the keyboard
    is still animating in). Never press the field first: when the keyboard is already up (the code screen
    autofocuses), the press can land on a key and type into the field, which changes its label. Only as a
    last resort, focus the field with a press and retry."""
    for attempt in range(5):
        n = wait_for(label, kind, timeout)
        out = ad('fill', n['ref'], text)
        print('  fill', label, '->', out.strip().splitlines()[0][:40])
        if 'Filled' in out:
            return
        time.sleep(2.0)
        if attempt == 3:
            n = wait_for(label, kind, timeout)
            ad('press', n['ref'])
            time.sleep(1.0)
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
