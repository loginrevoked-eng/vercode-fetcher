import os
import json
import argparse
from dataclasses import dataclass, fields

@dataclass
class Config:
    """Global application config - NOT user-specific"""
    poll_interval: int = 60
    max_linkcache: int = 100
    port: int = 8080
    host: str = "0.0.0.0"
    imap_reconnect_retries: int = 3
    
    def from_env(self):
        for field in fields(self):
            if field.name.upper() in os.environ:
                setattr(self, field.name, os.environ[field.name.upper()])
        return self
    
    def from_dict(self, data: dict):
        for field in fields(self):
            if field.name in data:
                setattr(self, field.name, data[field.name])
        return self
    
    def from_json(self, json_file: str):
        if not os.path.exists(json_file):
            return self
        with open(json_file, 'r') as f:
            data = json.load(f)
        return self.from_dict(data)
    
    def from_argv(self, prog: str = "otp_publisher", description: str = "OTP Publisher Server"):
        parser = argparse.ArgumentParser(prog=prog, description=description)
        for field in fields(self):
            flag = f"--{field.name.lower().replace(' ', '-').replace('_', '-')}"
            kwargs = {
                "default": getattr(self, field.name),
                "help": field.name,
                "type": field.type
            }
            if field.type == bool:
                kwargs["action"] = "store_true"
                del kwargs["type"]
            parser.add_argument(flag, **kwargs)
        args = parser.parse_args()
        return self.from_dict(vars(args))

