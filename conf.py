import os
import json
import tomllib
from argparse import ArgumentParser
from dataclasses import dataclass, field, fields


@dataclass
class Env:
    email: str = field(default="")
    password: str = field(default="")
    maglink_regex: str = field(default="")
    imap_host: str = field(default="")
    email_password: str = field(default="")
    imap_filter_query: str = field(default="")
    vercode_pagemarker: str = field(default="")
    vercode_regex: str = field(default="")
    poll_interval: int = field(default=60)
    max_linkcache: int = field(default=100)
    notification_title: str = field(default="Magic Link Push Notification")
    home_page: str = field(default="static/maglinks.html")
    app_title: str = field(default="Magic Link Push Notification")
    poll_url: str = field(default="/notifications")
    appjs: str = field(default="static/app.js")
    reduce_links: int = field(default=10)
    host: str = field(default="127.0.0.1")
    port: int = field(default=8000)
    is_deployed: bool = field(default=False)
    poll_endpoint: str = field(default="/notifications")
    imap_reconnect_retries: int = field(default=3)


    def from_file(self, path: str) -> "Env":
        if path.endswith(".toml"):
            return self.from_toml(path)
        elif path.endswith(".json"):
            return self.from_json(path)
        else:
            raise ValueError(f"Unsupported file format: {path}")

    def _set(self, name: str, value) -> None:
        if value is None:
            return
        f = next((f for f in fields(self) if f.name == name), None)
        if f:
            setattr(self, name, f.type(value))

    def _apply(self, data: dict) -> "Env":
        for f in fields(self):
            self._set(f.name, data.get(f.name))
        return self

    @staticmethod
    def read_file(path: str) -> str | None:
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            return f.read()

    def _validate(self) -> "Env":
        required = ["email", "imap_host", "email_password", "maglink_regex", "imap_filter_query"]
        for name in required:
            if not getattr(self, name, None):
                raise ValueError(f"{name} is missing or empty")
        return self

    def from_env(self) -> "Env":
        data = {f.name: os.getenv(f.name.upper()) for f in fields(self)}
        return self._apply(data)._validate()

    def from_dict(self, data: dict) -> "Env":
        return self._apply(data)._validate()

    def from_toml(self, path: str) -> "Env":
        content = Env.read_file(path)
        if content is None:
            raise FileNotFoundError(f"Config file not found: {path}")
        return self.from_dict(tomllib.loads(content))

    def from_json(self, path: str) -> "Env":
        with open(path, "r") as f:
            return self.from_dict(json.load(f))

    def from_argv(self) -> "Env":
        parser = ArgumentParser()
        for f in fields(self):
            parser.add_argument(f"--{f.name.replace('_', '-')}", type=f.type)
        return self._apply(vars(parser.parse_args()))._validate()


