#!/usr/bin/env python3
"""Worked example: PR #675 signed-out checkout (phone sign-up -> name -> email -> shipping address with
"Use my current location"). Copy this file, rewrite the steps for the feature at hand, keep the shape:

  * one mark() per action, written just before it
  * every tap()/fill() re-reads the screen, so refs never go stale
  * wait_for() the NEXT state instead of sleeping and hoping
  * short sleeps only where a viewer needs time to read the screen

Run a dry run first:   DEMO_NO_RECORD=1 python3 flow_example.py
Then the real take:    DEMO_DIR=/path/to/out python3 flow_example.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

BUNDLE = 'mobile.shopit.store'  # what `expo run:ios` installs; the older 'mobile.shopit.store.dev' may be stale
# Clerk dev instances accept fictional numbers +1 (xxx) 555-0100 .. 0199 with the fixed code 424242. A number
# that has already signed up signs INTO its existing account (name/email/address already saved, so those
# sheets never appear). Use a number that has not completed sign-up for a fresh-account demo.
PHONE = os.environ.get('DEMO_PHONE', '2015550103')
CODE = '424242'
EMAIL = 'jane.tester+demo@example.com'


def main():
    # ---- state reset, off camera -------------------------------------------------------------
    lib.set_location(37.3349, -122.0090)          # Apple Park, a valid US point
    lib.reset_permission('location', BUNDLE)      # so the system permission prompt shows on camera
    # (start from a signed-out Home; call lib.sign_out() first if the app is signed in)

    with lib.recording():
        lib.mark('Start signed out on Home. The simulator location is set to Apple Park, California')
        time.sleep(2.5)

        lib.mark('Open the product')
        lib.tap('Gibson Home Woodland Fox Salt & Pepper Set, $23.92', 'button')
        lib.wait_for('Add to Cart', 'other')
        time.sleep(1.5)

        lib.mark('Tap Add to Cart. Signed out, so the phone sign-in sheet opens')
        lib.tap('Add to Cart', 'other')
        lib.wait_for('Phone number', 'text-field')

        lib.mark('Enter a test phone number and continue')
        lib.fill('Phone number', PHONE)
        lib.tap('Continue with phone number', 'button')
        lib.wait_for('Verification code', 'text-field')

        lib.mark('Enter the test verification code')
        lib.fill('Verification code', CODE)
        lib.wait_for('Cart, 1 item', 'button', 40)   # disabled ("In progress") until sign-in finishes
        time.sleep(1.5)

        lib.mark('Open the cart')
        lib.tap('Cart, 1 item', 'button')
        lib.wait_for('Checkout')

        lib.mark('Tap Checkout. A missing name opens the name sheet')
        lib.tap('Checkout')
        end = time.time() + 25
        while time.time() < end and len([n for n in lib.snap() if n['kind'] == 'text-field' and not n['label']]) < 2:
            time.sleep(0.8)
        time.sleep(2.5)

        lib.mark('Type the first name. The keyboard opens and the sheet stays above it')
        lib.fill_unlabeled(0, 'Jane')
        time.sleep(4)                                  # the QWERTY keyboard only appears once typing starts
        lib.mark('Type the last name')
        lib.fill_unlabeled(0, 'Tester')                # index 0 again: field 0 now carries the label "Jane"
        lib.mark('Save and continue')
        for _ in range(3):                             # a first tap right after the keyboard opens can miss
            lib.tap('Save & Continue')
            time.sleep(4)
            if lib.find(lib.snap(), 'Email address', 'text-field'):
                break

        lib.mark('Checkout asks for an email. Enter one and save')
        lib.fill('Email address', EMAIL)
        lib.tap('Save & Continue')
        lib.wait_for('Use my current location', 'button', 40)
        time.sleep(2)

        nodes = lib.snap()
        assert lib.find(nodes, 'Jane', 'text-field', exact=True), 'first name was not prefilled'
        assert lib.find(nodes, 'Tester', 'text-field', exact=True), 'last name was not prefilled'
        lib.mark('The shipping sheet opens with first and last name already filled in')
        time.sleep(3)

        lib.mark('Tap Use my current location')
        lib.tap('Use my current location', 'button')
        lib.wait_for('Allow While Using App', 'button', 20)   # system alert, reachable through agent-device
        time.sleep(1.5)
        lib.mark('Location permission prompt. Allow While Using App')
        lib.tap('Allow While Using App', 'button')
        lib.wait_for('1 Apple Park Way', 'text-field', 25)
        time.sleep(5)
        lib.mark('Address, city, state and ZIP filled from the location')

        lib.mark('Save and continue')
        lib.tap('Save & Continue')
        lib.wait_for('Pay US', None, 40)                # Stripe payment sheet; stop here, never pay
        time.sleep(4)
        lib.mark('Checkout reaches the payment sheet. Stopping without paying')


if __name__ == '__main__':
    main()
