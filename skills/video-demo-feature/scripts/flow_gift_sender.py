#!/usr/bin/env python3
"""PR #675 gifter flow: signed out -> Send Gift -> phone sign-in -> recipient -> compose -> email -> Stripe TEST pay."""
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, '/Users/guilhermereis/Desktop/clones/shopit-monorepo/.claude/skills/video-demo-feature/scripts')
import lib  # noqa: E402

GIFTER = '2015550107'
GIFTEE = '2015550108'
CODE = '424242'
GIFTEE_ROW = f'+1 ({GIFTEE[:3]}) {GIFTEE[3:6]}-{GIFTEE[6:]}'
EMAIL = 'grrbm2@gmail.com'
CARD, EXP, CVC, ZIP = '4242424242424242', '0333', '333', '94105'


def shown(limit=14):
    for n in lib.snap():
        if n['kind'] not in ('text', 'key', 'menu-item') and n['label'] and 'keyboard' not in n['label'].lower():
            print('   ', n['ref'], n['kind'], n['label'][:70], n['rest'][:16])
            limit -= 1
            if limit <= 0:
                break


def fill_once(label, text, kind='text-field'):
    """Stripe fields report TEXT_ENTRY_MISMATCH yet accept the value, so never retry them."""
    n = lib.wait_for(label, kind)
    lib.ad('press', n['ref'])
    time.sleep(0.7)
    n = lib.wait_for(label, kind)
    print('  fill', label, '->', lib.ad('fill', n['ref'], text).strip().splitlines()[0][:50])
    time.sleep(0.8)


def pick_product():
    for n in lib.snap():
        m = re.search(r'\$(\d+)\.\d\d', n['label'])
        if n['kind'] == 'button' and m and int(m.group(1)) < 100 and 'Gift Card' not in n['label']:
            return n['label']
    raise SystemExit('no product under $100 on screen')


def main():
    lib.set_location(37.3349, -122.0090)
    # start from a clean app: an earlier take can leave a sheet open over Home
    subprocess.run(['xcrun', 'simctl', 'terminate', lib.UDID, 'mobile.shopit.store'], capture_output=True)
    lib.ad('open', 'mobile.shopit.store', '--platform', 'ios', '--device', 'iPhone 16e', '--foreground')
    end = time.time() + 60
    while time.time() < end:
        snap = lib.snap()
        if lib.find(snap, 'Open profile', 'button') or lib.find(snap, 'Sign in', 'button'):
            break
        time.sleep(2)
    if lib.find(lib.snap(), 'Open profile', 'button'):
        lib.sign_out()
    lib.ad('scroll', 'top')
    time.sleep(1)
    product = pick_product()
    print('product:', product)

    with lib.recording():
        lib.mark('Start signed out on Home')
        time.sleep(2.5)
        lib.mark('Open a product under one hundred dollars')
        lib.tap(product, 'button')
        lib.wait_for('Send Gift', 'other')
        time.sleep(1.5)
        if lib.find(lib.snap(), 'Size, Medium', 'button'):
            lib.tap('Size, Medium', 'button')
            time.sleep(1)

        lib.mark('Tap Send Gift while signed out. The phone sign-in sheet opens')
        lib.tap('Send Gift')
        lib.wait_for('Phone number', 'text-field')
        time.sleep(1.5)
        lib.mark('Enter a phone number and continue')
        lib.fill('Phone number', GIFTER)
        lib.tap('Continue with phone number', 'button')
        lib.wait_for('Verification code', 'text-field')
        lib.mark('Enter the verification code')
        time.sleep(2.5)
        lib.fill('Verification code', CODE)
        lib.wait_for('Send Gift', 'other', 40)
        time.sleep(2)

        lib.mark('Signed in. Tap Send Gift again')
        lib.tap('Send Gift')
        lib.wait_for('Search friends or enter a phone number', 'text-field')
        time.sleep(1.5)
        lib.mark('Type the phone number of the person to send the gift to')
        lib.fill('Search friends or enter a phone number', GIFTEE)
        lib.wait_for(GIFTEE_ROW, 'button')
        time.sleep(1.5)
        lib.tap(GIFTEE_ROW, 'button')
        lib.wait_for('Review and pay', 'other')
        time.sleep(1.5)

        lib.mark('Write a short gift note')
        note = 'Thinking of you. Enjoy!'
        lib.fill('gift-message-input', note, 'text-view')
        time.sleep(1.5)
        lib.mark('Tap Review and pay')
        lib.tap('Review and pay')

        end = time.time() + 40
        while time.time() < end:
            s = lib.snap()
            if lib.find(s, 'Email address', 'text-field') or lib.find(s, 'Card number', 'text-field'):
                break
            time.sleep(1)
        if lib.find(lib.snap(), 'Email address', 'text-field'):
            lib.mark('A new account needs a name and an email. Enter them and save')
            lib.fill('details-first-name-input', 'Sam')
            time.sleep(1)
            lib.fill('details-last-name-input', 'Gifter')
            time.sleep(1)
            lib.fill('Email address', EMAIL)
            time.sleep(1)
            lib.tap('Save & Continue')
            lib.wait_for('Review and pay', 'other', 40)
            time.sleep(2)
            s = lib.snap()
            if not lib.find(s, note, 'text-view', exact=True):
                print('  note was cleared by the email sheet, retyping')
                lib.fill('gift-message-input', note, 'text-view')
                time.sleep(1)
            lib.mark('Tap Review and pay again')
            lib.tap('Review and pay')
            lib.wait_for('Card number', 'text-field', 40)

        time.sleep(2)
        lib.mark('The Stripe payment sheet opens in test mode. Enter the test card')
        fill_once('Card number', CARD)
        fill_once('expiration date', EXP)
        fill_once('CVC', CVC)
        fill_once('Email', EMAIL)
        fill_once('ZIP', ZIP)
        time.sleep(1.5)
        lib.ad('scroll', 'down')
        time.sleep(1.5)
        pay = next((n for n in lib.snap() if n['kind'] == 'button' and n['label'].startswith('Pay $')), None)
        print('pay button:', pay and (pay['ref'], pay['label'], pay['rest']))
        if not pay or '[disabled]' in pay['rest']:
            print('PAY BUTTON NOT READY')
            shown()
            return
        lib.mark('Tap Pay')
        print('  ', lib.ad('press', pay['ref']).strip().splitlines()[0][:80])
        time.sleep(15)
        lib.mark('The gift is sent')
        time.sleep(4)
        print('after pay:')
        shown()

    # off camera: keep the claim link for the recipient side
    lib.tap('Copy link')
    time.sleep(1.5)
    link = subprocess.run(['xcrun', 'simctl', 'pbpaste', lib.UDID], capture_output=True, text=True).stdout.strip()
    open(os.path.join(lib.DEMO_DIR, 'claim-link.txt'), 'w').write(link)
    print('claim link:', link)


if __name__ == '__main__':
    main()
