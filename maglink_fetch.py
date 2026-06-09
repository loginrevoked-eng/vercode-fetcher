import re
import time
import email
import imaplib
from conf import Env
from datetime import datetime



class MaglinkFetcher:
    def __init__(self, config_path: str = "configuration.toml", env: Env = None):
        self.links = [{
            "title": "Nothing New yet!",
            "timestamp": datetime.now().isoformat(),
            "detail": "No new notifications found",
            "isUnread": True
        }]
        self.env = env or Env().from_toml(config_path).from_env().from_argv()
        self._connect()

    def _connect(self):
        self.mail = imaplib.IMAP4_SSL(self.env.imap_host)
        self.mail.login(self.env.email, self.env.email_password)

    def _extract_maglink(self, msg: email.message.Message) -> str | None:
        if msg.is_multipart():
            return None
        try:
            payload = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        except:
            return None

        match = re.search(self.env.maglink_regex, payload)
        return match.group(0) if match else None

    def _fetch_unseen_anthropic_inboxes(self) -> list[bytes]:
        self.mail.select('inbox')
        _, data = self.mail.search(None, self.env.filter_query)
        return data[0].split()

    def _fetch_message(self, msg_id: bytes) -> email.message.Message:
        _, data = self.mail.fetch(msg_id, '(RFC822)')
        return email.message_from_bytes(data[0][1])

    def _mark_seen(self, msg_id: bytes):
        self.mail.store(msg_id, '+FLAGS', '\\Seen')

    def _collect_maglinks(self) -> dict[str, str]:
        maglinks = []
        for msg_id in self._fetch_unseen_anthropic_inboxes():
            msg = self._fetch_message(msg_id)
            maglink = self._extract_maglink(msg)
            if maglink:
                maglinks.append({
                    "title": self.env.notification_title,
                    "timestamp": msg["Date"],
                    "detail": maglink,
                    "isUnread": True
                })
            self._mark_seen(msg_id)
        return maglinks

    def mark_read(self, maglinks: list[dict[str, str]]):
        for maglink in maglinks:
            maglink["isUnread"] = False
        
    def mark_last20_read(self):
        for maglink in self.links[-20:]:
            maglink["isUnread"] = False
    
    def reduce_links(self):
        for i in range(self.env.reduce_links):
            self.links.pop(-1)

    def poll_once(self):
        try:
            maglinks = self._collect_maglinks()
            if len(self.links) < self.env.max_linkcache:
                self.links.extend(maglinks)
            else:self.reduce_links()
            return maglinks
        except Exception:
            return []

    def start_polling(self):
        while True:
            for maglink in self.poll_once():
                print(f"{maglink['detail']} - {maglink['timestamp']}")
            time.sleep(self.env.poll_interval)

    def last_20(self):
        last_20_ = self.links[-20:]
        # Only mark real maglinks as read, not the default "Nothing New yet!" notification
        real_maglinks = [link for link in last_20_ if link["title"] != "Nothing New yet!"]
        self.mark_read(real_maglinks)
        return last_20_


if __name__ == "__main__":
    MaglinkFetcher().start_polling()