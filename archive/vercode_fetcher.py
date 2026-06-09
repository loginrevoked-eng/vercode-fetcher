import re
import time
import email
import imaplib
from conf import Env
from playwright.sync_api import sync_playwright




class ClaudeVercodeExtractor:
    def __init__(self, config_path: str = "configuration.toml"):
        self.env = Env().from_toml(config_path).from_env().from_argv()
        self._connect()

    def _connect(self):
        print(f"Connecting to IMAP server: {self.env.imap_host}")
        self.mail = imaplib.IMAP4_SSL(self.env.imap_host)
        print(f"Logging in as: {self.env.email}")
        self.mail.login(self.env.email, self.env.email_password)
        print("Successfully connected and logged in")

    def _extract_maglink(self, msg: email.message.Message) -> str | None:
        if msg.is_multipart():return None
        
        try:
            payload = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        except:
            raise
            return None
        
        match = re.search(self.env.maglink_regex, payload)
        return match.group(0) if match else None

    def _fetch_unseen_anthropic_inboxes(self) -> list[bytes]:
        self.mail.select('inbox')
        print(f"Searching with query: {self.env.filter_query}")
        
        # First try the configured query
        _, data = self.mail.search(None, self.env.filter_query)
        print(f"Configured query result: {data}")
        
        # Also try broader searches to debug
        _, all_unseen = self.mail.search(None, 'UNSEEN')
        print(f"All UNSEEN emails: {len(all_unseen[0].split())} emails")
        
        _, all_anthropic = self.mail.search(None, 'FROM "anthropic.com"')
        print(f"All emails from anthropic.com: {len(all_anthropic[0].split())} emails")
        
        _, recent = self.mail.search(None, 'ALL')
        recent_ids = recent[0].split()
        print(f"Total emails in inbox: {len(recent_ids)}")
        
        # Check the latest 5 emails to see senders
        if recent_ids:
            print("\nChecking latest 5 emails:")
            for msg_id in recent_ids[-5:]:
                msg = self._fetch_message(msg_id)
                print(f"  ID {msg_id}: From: {msg['From']}, Subject: {msg['Subject']}")
        
        return data[0].split()

    def _fetch_message(self, msg_id: bytes) -> email.message.Message:
        _, data = self.mail.fetch(msg_id, '(RFC822)')
        return email.message_from_bytes(data[0][1])

    def _mark_seen(self, msg_id: bytes):
        self.mail.store(msg_id, '+FLAGS', '\\Seen')

    def _get_vercode_from_url(self, url: str) -> str | None:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=False)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_function(
                f"() => document.body.innerText.includes('{self.env.vercode_pagemarker}')",
                timeout=0,
                polling=1000,
            )
            content = page.inner_text("body")
            browser.close()

        match = re.search(self.env.vercode_regex, content)
        return match.group(1) if match else None

    def _collect_vercodes(self) -> dict[str, str]:
        vercodes = {}
        
        print("Fetching unseen emails from Anthropic...")
        msg_ids = self._fetch_unseen_anthropic_inboxes()
        print(f"Found {len(msg_ids)} unseen emails")

        for msg_id in msg_ids:
            print(f"Processing message: {msg_id}")
            msg = self._fetch_message(msg_id)
            maglink = self._extract_maglink(msg)
            if maglink:
                print(f"Found magic link: {maglink}")
                vercode = self._get_vercode_from_url(maglink)
                if vercode:
                    print(f"Extracted verification code: {vercode}")
                    vercodes[vercode] = msg["Date"]
            else:
                print("No magic link found in this message")

            self._mark_seen(msg_id)

        return vercodes

    def poll_once(self):
        try:
            return self._collect_vercodes()
        except Exception as e:
            print(f"Error occurred: {e}")
            return {}

    def start_polling(self):
        print("Starting polling loop...")
        while True:
            print(f"Polling for new verification codes...")
            vercodes = self.poll_once()
            if vercodes:
                print(f"Found {len(vercodes)} new verification codes")
                for vercode, date in vercodes.items():
                    print(f"  {vercode} - {date}")
            else:
                print("No new verification codes found")
            print(f"Sleeping for {self.env.poll_interval} seconds...")
            time.sleep(self.env.poll_interval)


if __name__ == "__main__":
    ClaudeVercodeExtractor().start_polling()