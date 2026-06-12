import re
import time
import email
import imaplib
import logging
from conf import Env
from collections import deque
from datetime import datetime

logger = logging.getLogger(__name__)


class MaglinkFetcher:
    def __init__(self, config_path: str = "configuration.toml", env: Env = None):
        self.links: deque[dict] = deque(
            [{
                "title": "Nothing New yet!",
                "timestamp": datetime.now().isoformat(),
                "detail": "No new notifications found",
                "isUnread": True
            }],
            maxlen=None  # maxlen set after env is loaded
        )
        self.env = env or Env().from_toml(config_path).from_env().from_argv()
        self.links = deque(self.links, maxlen=self.env.max_linkcache)  # apply cap
        self._running = False
        self._connect()

    def _connect(self):
        self.mail = imaplib.IMAP4_SSL(self.env.imap_host)
        self.mail.login(self.env.email, self.env.email_password)

    def _extract_maglink(self, msg: email.message.Message) -> str | None:
        if msg.is_multipart():return None
        try:
            payload = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        except (AttributeError, UnicodeDecodeError) as e:
            logger.warning("Failed to decode message payload: %s", e)
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

    def _collect_maglinks(self) -> list[dict[str, str]]:
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

    def _mark_read(self, maglinks: list[dict[str, str]]):
        for maglink in maglinks:
            maglink["isUnread"] = False

    def mark_last20_read(self):
        links_list = list(self.links)
        for maglink in links_list[-20:]:
            maglink["isUnread"] = False

    def poll_once(self) -> list[dict[str, str]]:
        try:
            maglinks = self._collect_maglinks()
            # deque with maxlen handles capacity automatically — just extend
            self.links.extend(maglinks)
            return maglinks
        except imaplib.IMAP4.abort:
            logger.warning("IMAP connection dropped, reconnecting...")
            try:
                self._connect()
            except Exception as reconnect_err:
                logger.error("Reconnection failed: %s", reconnect_err)
            return []
        except Exception as e:
            logger.error("poll_once error: %s", e)
            return []

    def start_polling(self):
        self._running = True
        while self._running:
            for maglink in self.poll_once():
                print(f"{maglink['detail']} - {maglink['timestamp']}")
            time.sleep(self.env.poll_interval)

    def stop_polling(self):
        self._running = False

    def last_20(self) -> list[dict[str, str]]:
        last_20_ = list(self.links)[-20:]
        real_maglinks = [link for link in last_20_ if link["title"] != "Nothing New yet!"]
        self._mark_read(real_maglinks)
        return last_20_


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    MaglinkFetcher().start_polling()