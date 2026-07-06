import pyotp
import time


def repl():
    while True:
        secret = input("Enter secret: ").replace(" ", "").upper()
        if not secret:
            print("Exiting...")
            break
        totp = pyotp.TOTP(secret)
        print(f"Your Google 2FA Code is: {totp.now()}")
        time.sleep(1)

repl()
