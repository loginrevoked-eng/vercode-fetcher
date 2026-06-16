import os
import re
import email
import imaplib
import time
from conf import Env
from typing import Callable, List
from datetime import datetime
from dataclasses import dataclass
from logging import getLogger, FileHandler, StreamHandler, Formatter, DEBUG, WARNING






def setup_logging(log_file: str = "logs/empub.log", console_level: int = WARNING):
    if "/" in log_file or "\\" in log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    globals()["logger"] = getLogger(__name__)
    logger.setLevel(DEBUG)
    formatter = Formatter(
        "%(asctime)s — %(name)s — %(levelname)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = FileHandler(log_file)
    file_handler.setLevel(DEBUG)
    file_handler.setFormatter(formatter)
    console_handler = StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

def panic(msg:str="PANIC!", tag:str="PANIC!", code:int=1):
    logger.error(
        f":( {tag}: {msg}"
    )
    exit(code)




@dataclass
class Notification:
    title: str
    timestamp: str
    detail: str
    read: bool

    @classmethod
    def new(cls, title: str = "Nothing New Yet", detail: str = "No new notifications found"):
        return cls(
            title=title,
            timestamp=datetime.now().isoformat(),
            detail=detail,
            read=False,
        )

    def to_dict(self):
        return {
            "title": self.title,
            "timestamp": self.timestamp,
            "detail": self.detail,
            "isUnread": not self.read,
        }

    def mark_read(self):
        self.read = True
        return self
    
    def is_unread(self):
        return not self.read


class NotiPublisher:
    def __init__(self, env: Env = None, config_path: str = "configuration.toml"):
        self.env = env or Env().from_file(config_path).from_env().from_argv()
        self.last20_pushes: List[Notification] = [Notification.new()]
        logger.info(f"notification publisher initialized {f'with config_file: {config_path}'  if config_path else ''}")

    def _append(self, notification: Notification):
        self.last20_pushes.append(notification)
        if len(self.last20_pushes) > 20:
            self.last20_pushes.pop(0)
        logger.debug(f"notification appended: {repr(notification.detail)}")

    def just_in(self, maglink: str, title: str = "New Magic Link Found"):
        self._append(Notification.new(title=title, detail=maglink))

    def mark_read(self, noti_count: int = 20):
        for notification in self.last20_pushes[-noti_count:]:
            notification.read = True
            logger.debug(f"notification marked as read: {repr(notification.detail)}")

    def consume20(self):
        for notification in self.last20_pushes:
            logger.debug(f"notification consumed: {repr(notification.detail)}")
            yield notification


class ImapClient:
    def __init__(self, env: Env):
        self.env = env
        self.mail = None
        logger.info("Imap client initialized")

    def connect(self, retries: int = None):
        retries = retries or self.env.imap_reconnect_retries
        for i in range(1, retries + 1):
            try:
                self.mail = imaplib.IMAP4_SSL(self.env.imap_host)
                self.mail.login(self.env.email, self.env.email_password)
                logger.info(f"Connected to IMAP server on attempt #{i}")
                break
            except Exception as e:
                logger.error(f"Attempt #{i} to connect to IMAP server failed:\nException: {e}")
                if i == retries:
                    panic(f"Failed to connect to IMAP server \nException:{e}", "IMAP_CONNECTION_ERROR")

    def connected(self) -> bool:
        try:
            return self.mail is not None and self.mail.noop()[0] == "OK"
        except Exception:
            return False

    def fetch_anthropic_unseen(self, filter_query: str = None) -> List[bytes] | None:
        filter_query = filter_query or self.env.imap_filter_query
        self.mail.select("inbox")
        status, messages = self.mail.search(None, filter_query)
        if status != "OK":
            logger.error("Failed to search for unseen emails")
            return None
        email_ids = messages[0].split()
        logger.debug(f"Found {len(email_ids)} unseen anthropic emails")
        return email_ids

    def fetch_email(self, email_id: bytes) -> bytes:
        status, msg_data = self.mail.fetch(email_id, "(RFC822)")
        if status != "OK":
            logger.error(f"Failed to fetch email {email_id}")
            return None
        return msg_data[0][1]

    def mark_seen(self, email_id: bytes):
        self.mail.store(email_id, "+FLAGS", "\\Seen")
        logger.debug(f"Marked email {repr(email_id)} as seen")

    def extract_maglink(self, email_id: bytes) -> str | None:
        raw = self.fetch_email(email_id)
        if raw is None:
            return None
        single_email = email.message_from_bytes(raw)
        if single_email.is_multipart():
            logger.debug(f"Email {repr(email_id)} is multipart, skipping...")
            return None
        try:
            payload = single_email.get_payload(decode=True).decode("utf-8", errors="ignore")
            match = re.search(self.env.maglink_regex, payload)
            maglink = match.group(0) if match else None
            logger.debug(f"Extracted maglink: {maglink}" if maglink else f"No maglink found in email {repr(email_id)}")
            return maglink
        except Exception as e:
            logger.error(f"Failed to decode email payload:\nException: {e}")


    def ensure_connected(self):
        if not self.connected():
            logger.error("Requirement not fulfilled: Not connected to IMAP server")
            panic("Requirement not fulfilled: Not connected to IMAP server", "IMAP_CONNECTION_ERROR")

    def poll_maglinks(self):
        self.ensure_connected()
        ids = self.fetch_anthropic_unseen()
        extracted = 0
        for mailid in ids:
            maglink = self.extract_maglink(mailid)
            if maglink:
                yield maglink
                extracted += 1
            self.mark_seen(mailid)
        logger.info(f"Polled {len(ids)} emails and extracted {extracted} magic links")


class MaglinkFetcher:
    def __init__(self, config_path: str = "configuration.toml", env: Env = None):
        self.env = env or Env().from_file(config_path)
        self.publisher = NotiPublisher(env=self.env)
        self.imap_client = ImapClient(env=self.env)
        self.connect()

        logger.info("Maglink fetcher initialized")

    def connect(self):
        try:
            self.imap_client.connect()
        except Exception as e:
            logger.error(f"Failed to connect to IMAP server:\nException: {e}")
            raise
        logger.info("Maglink fetcher connected to IMAP server")

    def poll_once(self):
        try:
            for maglink in self.imap_client.poll_maglinks():
                self.publisher.just_in(maglink)
        except Exception as e:
            logger.error(f"Failed to poll maglinks:\nException: {e}")
            raise

    def subfeed(self):
        try:
            self.poll_once()
            logger.info("Maglink fetcher polled once and subscriber will be fed")
        except Exception as e:
            logger.error(f"Failed to poll maglinks:\nException: {e}")
            raise
        return self.publisher.consume20()

    def poll_forever(self, handler:Callable[[str], Any]):
        while True:
            for maglink in self.subfeed():
                handler(maglink)


if __name__ == "__main__":
    setup_logging()
    logger.debug("Finished setting up logger, initializing maglink fetcher...")
    fetcher = MaglinkFetcher()
    def handle_notification(notification):
        if notification.is_unread():
            print(notification)
            notification.mark_read()
        time.sleep(1)
    fetcher.poll_forever(handle_notification)
    