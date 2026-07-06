import re
import time
import email
import imaplib
from conf import Config
from typing import Callable, List, Dict, Optional
from data_models import Notification
from logger import setup_logging, panic
from subscriptions import Subscription
from user_manager import UserManager, UserConfig



logger = setup_logging("logs/maglink_fetch.log", level="INFO")



class NotiPublisher:
    def __init__(self, max_cache: int = 20):
        self.max_cache = max_cache
        self.last20_pushes: List[Notification] = [Notification.new()]
        logger.info(f"notification publisher initialized with max_cache={max_cache}")

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
    """IMAP client for a specific user and provider"""
    
    def __init__(self, user_config: UserConfig, provider_name: str, provider_config, imap_reconnect_retries: int = 3):
        self.user_config = user_config
        self.provider_name = provider_name
        self.provider_config = provider_config
        self.imap_reconnect_retries = imap_reconnect_retries
        self.mail = None
        logger.info(f"IMAP client initialized for {user_config.email} with {provider_name} provider")

    def connect(self, retries: int = None):
        retries = retries or self.imap_reconnect_retries
        for i in range(1, retries + 1):
            try:
                self.mail = imaplib.IMAP4_SSL(self.user_config.imap_host)
                self.mail.login(self.user_config.email, self.user_config.email_password)
                logger.info(f"Connected to IMAP server on attempt #{i} for {self.user_config.email}")
                break
            except Exception as e:
                logger.error(f"Attempt #{i} to connect to IMAP server failed: {e}")
                if i == retries:
                    panic(f"Failed to connect to IMAP server for {self.user_config.email}: {e}", "IMAP_CONNECTION_ERROR")

    def connected(self) -> bool:
        try:
            return self.mail is not None and self.mail.noop()[0] == "OK"
        except Exception:
            return False

    def fetch_unseen_emails(self) -> List[bytes]:
        """Fetch unseen emails using provider's filter query"""
        self.mail.select("inbox")
        filter_query = self.provider_config.imap_filter_query
        status, messages = self.mail.search(None, filter_query)
        if status != "OK":
            logger.error(f"Failed to search for unseen emails with query: {filter_query}")
            return []
        email_ids = messages[0].split()
        logger.debug(f"Found {len(email_ids)} unseen emails for {self.provider_name}")
        return email_ids

    def fetch_email(self, email_id: bytes) -> Optional[bytes]:
        status, msg_data = self.mail.fetch(email_id, "(RFC822)")
        if status != "OK":
            logger.error(f"Failed to fetch email {email_id}")
            return None
        return msg_data[0][1]

    def mark_seen(self, email_id: bytes):
        self.mail.store(email_id, "+FLAGS", "\\Seen")
        logger.debug(f"Marked email {repr(email_id)} as seen")

    def ensure_connected(self):
        if not self.connected():
            logger.error("Requirement not fulfilled: Not connected to IMAP server")
            panic("Requirement not fulfilled: Not connected to IMAP server", "IMAP_CONNECTION_ERROR")

    def _decode_email(self, raw_email: bytes) -> Optional[str]:
        """Decode email content"""
        try:
            msg = email.message_from_bytes(raw_email)
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        return part.get_payload(decode=True).decode("utf-8", errors="ignore")
                return None
            else:
                return msg.get_payload(decode=True).decode("utf-8", errors="ignore")
        except Exception as e:
            logger.error(f"Failed to decode email: {e}")
            return None
    
    def poll_maglinks(self):
        """Poll for magic links"""
        self.ensure_connected()
        ids = self.fetch_unseen_emails()
        extracted = 0
        for mailid in ids:
            raw_email = self.fetch_email(mailid)
            if raw_email:
                payload = self._decode_email(raw_email)
                if payload:
                    match = re.search(self.provider_config.maglink_regex, payload)
                    if match:
                        maglink = match.group(0)
                        logger.info(f"Extracted magic link: {maglink}")
                        yield maglink
                        extracted += 1
            self.mark_seen(mailid)
        logger.info(f"Polled {len(ids)} emails and extracted {extracted} magic links for {self.provider_name}")
    
    def poll_vercodes(self):
        """Poll for verification codes"""
        self.ensure_connected()
        ids = self.fetch_unseen_emails()
        extracted = 0
        for mailid in ids:
            raw_email = self.fetch_email(mailid)
            if raw_email:
                payload = self._decode_email(raw_email)
                if payload:
                    match = re.search(self.provider_config.vercode_regex, payload)
                    if match:
                        vercode = match.group(1) if match.groups() else match.group(0)
                        logger.info(f"Extracted verification code: {vercode}")
                        yield vercode
                        extracted += 1
            self.mark_seen(mailid)
        logger.info(f"Polled {len(ids)} emails and extracted {extracted} verification codes for {self.provider_name}")


class MaglinkFetcher:
    """
    Multi-user, multi-provider verification code fetcher.
    Manages subscriptions for multiple users across different providers.
    """
    
    def __init__(self, users_dir: str = "users", global_config: Config = None):
        self.global_config = global_config or Config().from_json("configuration.json").from_env()
        self.user_manager = UserManager(users_dir)
        
        # subscriptions[user_id][provider_name] = Subscription
        self.subscriptions: Dict[str, Dict[str, Subscription]] = {}
        
        self._initialize_subscriptions()
        logger.info(f"Maglink fetcher initialized with {len(self.subscriptions)} users")

    def _initialize_subscriptions(self):
        """Create subscriptions for all users and their enabled providers"""
        for email, user_config in self.user_manager.get_all_users().items():
            self.subscriptions[email] = {}
            
            for provider_name in user_config.get_enabled_providers():
                provider_config = user_config.providers[provider_name]
                
                # Create IMAP client
                imap_client = ImapClient(
                    user_config=user_config,
                    provider_name=provider_name,
                    provider_config=provider_config,
                    imap_reconnect_retries=self.global_config.imap_reconnect_retries
                )
                
                # Create notification publisher
                publisher = NotiPublisher(max_cache=self.global_config.max_linkcache)
                
                # Create subscription
                subscription = Subscription(
                    user_id=email,
                    provider_name=provider_name,
                    user_config=user_config,
                    provider_config=provider_config,
                    publisher=publisher
                )
                
                # Store subscription (keyed by email)
                self.subscriptions[email][provider_name] = subscription
                
                # Connect IMAP client
                try:
                    imap_client.connect()
                    # Store client in subscription for later use
                    subscription.imap_client = imap_client
                    logger.info(f"Connected subscription: {email}/{provider_name}")
                except Exception as e:
                    logger.error(f"Failed to connect {email}/{provider_name}: {e}")

    def get_subscription(self, email: str, provider_name: str) -> Optional[Subscription]:
        """Get a specific subscription by email and provider"""
        return self.subscriptions.get(email, {}).get(provider_name)

    def poll_once(self, email: str, provider_name: str):
        """Poll for new maglinks/vercodes for a specific email/provider"""
        subscription = self.get_subscription(email, provider_name)
        if not subscription:
            logger.error(f"Subscription not found: {email}/{provider_name}")
            return
        
        try:
            for maglink in subscription.imap_client.poll_maglinks():
                subscription.publisher.just_in(maglink, title=f"New {provider_name} Magic Link")
            
            for vercode in subscription.imap_client.poll_vercodes():
                subscription.publisher.just_in(vercode, title=f"New {provider_name} Verification Code")
                
        except Exception as e:
            logger.error(f"Failed to poll {email}/{provider_name}: {e}")
            raise

    def get_feed(self, email: str, provider_name: str):
        """Get notification feed for a specific email/provider"""
        subscription = self.get_subscription(email, provider_name)
        if not subscription:
            logger.error(f"Subscription not found: {email}/{provider_name}")
            return []
        
        try:
            self.poll_once(email, provider_name)
            return list(subscription.publisher.consume20())
        except Exception as e:
            logger.error(f"Failed to get feed for {email}/{provider_name}: {e}")
            return []

    def poll_forever(self, email: str, provider_name: str, handler: Callable[[Notification], None]):
        """Continuously poll for a specific email/provider"""
        subscription = self.get_subscription(email, provider_name)
        if not subscription:
            logger.error(f"Subscription not found: {email}/{provider_name}")
            return
        
        while True:
            for notification in self.get_feed(email, provider_name):
                handler(notification)
            time.sleep(self.global_config.poll_interval)


if __name__ == "__main__":
    setup_logging()
    logger.info("Initializing maglink fetcher...")
    fetcher = MaglinkFetcher()
    
    def handle_notification(notification):
        if notification.is_unread():
            print(notification)
            notification.mark_read()
    
    # Example: poll for loginrevoked@gmail.com's claude provider
    email = "loginrevoked@gmail.com"
    if fetcher.subscriptions.get(email, {}).get("claude"):
        fetcher.poll_forever(email, "claude", handle_notification)
    