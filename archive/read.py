import imaplib, email, re
from playwright.sync_api import sync_playwright

def get_vercode(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        
        page.wait_for_function(
            "() => document.body.innerText.includes('Use verification code to continue')",
            timeout=0,
            polling=1000
        )
        
        content = page.inner_text("body")
        browser.close()
        
        match = re.search(r'\b(\d{6})\b', content)
        return match.group(1) if match else None

mail = imaplib.IMAP4_SSL('imap.gmail.com')
mail.login('loginrevoked@gmail.com', 'dsog mgzx asiz bsjm')
mail.select('inbox')

ids = mail.search(None, 'FROM "mail.anthropic.com"')[1][0].split()

msg = email.message_from_bytes(
    mail.fetch(ids[-1], '(BODY.PEEK[])')[1][0][1]
)

if msg.is_multipart():
    print(f"Message is multipart with {len(msg.get_payload())} parts")
    exit()
else:
    match = re.search(r'https://claude\.ai/magic-link#\S+', msg.get_payload(decode=True).decode())
    if match:
        vercode = get_vercode(match.group(0))
        print(vercode)