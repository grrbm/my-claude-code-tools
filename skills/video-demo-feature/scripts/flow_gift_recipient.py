#!/usr/bin/env python3
"""PR #675 recipient flow: claim link -> phone sign-in -> name+email sheet -> address (location) -> accept."""
import os
import subprocess
import sys
import time

sys.path.insert(0, '/Users/guilhermereis/Desktop/clones/shopit-monorepo/.claude/skills/video-demo-feature/scripts')
import lib  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
LINK = open(os.path.join(HERE, 'gifter-video3', 'claim-link.txt')).read().strip()
GIFTEE = '2015550108'
CODE = '424242'


def shot(name):
    subprocess.run(['xcrun', 'simctl', 'io', lib.UDID, 'screenshot', os.path.join(lib.DEMO_DIR, name)], capture_output=True)


def main():
    print('claim link:', LINK)
    lib.set_location(37.3349, -122.0090)
    lib.reset_permission('location', 'mobile.shopit.store')
    subprocess.run(['xcrun', 'simctl', 'terminate', lib.UDID, 'mobile.shopit.store'], capture_output=True)
    lib.ad('open', 'mobile.shopit.store', '--platform', 'ios', '--device', 'iPhone 16e', '--foreground')
    end = time.time() + 60
    while time.time() < end:
        s = lib.snap()
        if lib.find(s, 'Open profile', 'button') or lib.find(s, 'Sign in', 'button'):
            break
        time.sleep(2)
    if lib.find(lib.snap(), 'Open profile', 'button'):
        lib.sign_out()

    with lib.recording():
        lib.mark('The recipient taps the claim link')
        time.sleep(2)
        subprocess.run(['xcrun', 'simctl', 'openurl', lib.UDID, LINK], check=True)
        lib.wait_for('Phone number', 'text-field', 40)
        time.sleep(1)
        shot('giftee-sealed-gift.png')
        time.sleep(4)

        lib.mark('Sign in with the phone number the gift was sent to')
        lib.fill('Phone number', GIFTEE)
        time.sleep(1)
        lib.tap('Continue with phone number', 'button')
        lib.wait_for('Verification code', 'text-field')
        lib.mark('Enter the verification code')
        time.sleep(2.5)
        lib.fill('Verification code', CODE)
        lib.wait_for('Claim gift', 'button', 40)
        time.sleep(3)

        lib.mark('Signed in as a brand-new recipient. Tap Claim gift')
        lib.tap('Claim gift', 'button')
        lib.wait_for('details-first-name-input', 'text-field', 40)
        time.sleep(2.5)
        lib.mark('A new recipient is asked for name and email once')
        lib.fill('details-first-name-input', 'Riley')
        time.sleep(1.5)
        lib.fill('details-last-name-input', 'Giftee')
        time.sleep(1.5)
        lib.fill('Email address', 'riley.giftee@example.com')
        time.sleep(2)
        lib.mark('Tap Save and Continue')
        lib.tap('Save & Continue')

        lib.wait_for('Use my current location', 'button', 40)
        time.sleep(3)
        nodes = lib.snap()
        assert lib.find(nodes, 'Riley', 'text-field', exact=True), 'first name not prefilled'
        assert lib.find(nodes, 'Giftee', 'text-field', exact=True), 'last name not prefilled'
        lib.mark('The address sheet opens with the name already filled in. Tap Use my current location')
        time.sleep(2)
        lib.tap('Use my current location', 'button')
        deadline = time.time() + 25
        while time.time() < deadline:
            s = lib.snap()
            if lib.find(s, 'Allow While Using App', 'button'):
                lib.mark('Allow location')
                time.sleep(1.5)
                lib.tap('Allow While Using App', 'button')
                break
            if lib.find(s, '1 Apple Park Way', 'text-field'):
                break
            time.sleep(1)
        lib.wait_for('1 Apple Park Way', 'text-field', 25)
        lib.mark('The address fills in from the location')
        time.sleep(4)
        lib.mark('Tap Save and Continue')
        lib.tap('Save & Continue')

        lib.wait_for('Accept', None, 40)
        time.sleep(4)
        lib.mark('Confirm the shipping details and tap Accept')
        lib.tap('Accept')
        lib.wait_for('Gift claimed!', None, 40)
        lib.mark('The gift is claimed')
        time.sleep(9)
        shot('giftee-claimed.png')


if __name__ == '__main__':
    main()
