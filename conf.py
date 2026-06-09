import os
import json
import tomllib
from argparse import ArgumentParser
from dataclasses import dataclass, field



@dataclass
class Env:
    email: str = field(default="")
    password: str = field(default="")
    maglink_regex: str = field(default="")
    imap_host: str = field(default="")
    email_password: str = field(default="")
    filter_query: str = field(default="")
    vercode_pagemarker: str = field(default="")
    vercode_regex: str = field(default="")
    poll_interval: int = field(default=60)
    max_linkcache: int = field(default=100)
    notification_title: str = field(default="Magic Link Push Notification")
    home_page: str = field(default="index.html")

    @staticmethod
    def read_file(path: str) -> str | None:
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            return f.read()

    def _validate(self) -> "Env":
        for fname, val in self.__dict__.items():
            if val is None or val == "":
                raise ValueError(f"{fname} is missing or empty")
        return self

    def from_env(self) -> "Env":
        if os.getenv("EMAIL"): self.email = os.getenv("EMAIL")
        if os.getenv("PASSWORD"): self.password = os.getenv("PASSWORD")
        if os.getenv("MAGLINK_REGEX"): self.maglink_regex = os.getenv("MAGLINK_REGEX")
        if os.getenv("IMAP_HOST"): self.imap_host = os.getenv("IMAP_HOST")
        if os.getenv("EMAIL_PASSWORD"): self.email_password = os.getenv("EMAIL_PASSWORD")
        if os.getenv("FILTER_QUERY"): self.filter_query = os.getenv("FILTER_QUERY")
        if os.getenv("VERCODE_PAGEMARKER"): self.vercode_pagemarker = os.getenv("VERCODE_PAGEMARKER")
        if os.getenv("VERCODE_REGEX"): self.vercode_regex = os.getenv("VERCODE_REGEX")
        if os.getenv("POLL_INTERVAL"): self.poll_interval = int(os.getenv("POLL_INTERVAL"))
        if os.getenv("MAX_LINKCACHE"): self.max_linkcache = int(os.getenv("MAX_LINKCACHE"))
        if os.getenv("NOTIFICATION_TITLE"): self.notification_title = os.getenv("NOTIFICATION_TITLE")
        if os.getenv("HOME_PAGE"): self.home_page = os.getenv("HOME_PAGE")
        return self._validate()

    def from_dict(self, data: dict) -> "Env":
        self.email = data.get("email")
        self.password = data.get("password")
        self.maglink_regex = data.get("maglink_regex")
        self.imap_host = data.get("imap_host")
        self.email_password = data.get("email_password")
        self.filter_query = data.get("filter_query")
        self.vercode_pagemarker = data.get("vercode_pagemarker")
        self.vercode_regex = data.get("vercode_regex")
        self.poll_interval = data.get("poll_interval", 60)
        self.max_linkcache = data.get("max_linkcache", 100)
        self.notification_title = data.get("notification_title", "Magic Link Push Notification")
        self.home_page = data.get("home_page", "index.html")
        return self._validate()

    def from_toml(self, path: str) -> "Env":
        content = Env.read_file(path)
        if content is None:
            raise FileNotFoundError(f"Config file not found: {path}")
        data = tomllib.loads(content)
        return self.from_dict(data)

    def from_json(self, path: str) -> "Env":
        with open(path, "r") as f:
            data = json.load(f)
        return self.from_dict(data)

    def from_argv(self) -> "Env":
        parser = ArgumentParser()
        parser.add_argument("--email", type=str)
        parser.add_argument("--password", type=str)
        parser.add_argument("--maglink-regex", type=str)
        parser.add_argument("--imap-host", type=str)
        parser.add_argument("--email-password", type=str)
        parser.add_argument("--filter-query", type=str)
        parser.add_argument("--vercode-pagemarker", type=str)
        parser.add_argument("--vercode-regex", type=str)
        parser.add_argument("--poll-interval", type=int)
        parser.add_argument("--max-linkcache", type=int)
        args = parser.parse_args()
        if args.email: self.email = args.email
        if args.password: self.password = args.password
        if args.maglink_regex: self.maglink_regex = args.maglink_regex
        if args.imap_host: self.imap_host = args.imap_host
        if args.email_password: self.email_password = args.email_password
        if args.filter_query: self.filter_query = args.filter_query
        if args.vercode_pagemarker: self.vercode_pagemarker = args.vercode_pagemarker
        if args.vercode_regex: self.vercode_regex = args.vercode_regex
        if args.poll_interval: self.poll_interval = args.poll_interval
        if args.max_linkcache: self.max_linkcache = args.max_linkcache
        if args.notification_title: self.notification_title = args.notification_title
        if args.home_page: self.home_page = args.home_page
        return self._validate()