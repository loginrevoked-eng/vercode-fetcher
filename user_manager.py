"""
User configuration management - loads per-user JSON configs
"""
import os
import json
from typing import Dict, Optional
from dataclasses import dataclass
from logger import setup_logging

logger = setup_logging("logs/user_manager.log", level="INFO")


@dataclass
class ProviderConfig:
    """Configuration for a specific provider (claude, chatgpt, etc)"""
    enabled: bool
    imap_filter_query: str
    maglink_regex: str
    vercode_regex: str
    vercode_pagemarker: str
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            enabled=data.get("enabled", True),
            imap_filter_query=data.get("imap_filter_query", "UNSEEN"),
            maglink_regex=data.get("maglink_regex", r"https?://\S+"),
            vercode_regex=data.get("vercode_regex", r"\b(\d{6})\b"),
            vercode_pagemarker=data.get("vercode_pagemarker", "verification code")
        )


@dataclass
class UserConfig:
    """Configuration for a single user"""
    user_id: str
    email: str
    email_password: str
    imap_host: str
    google_authenticator_secret: str
    providers: Dict[str, ProviderConfig]
    
    @classmethod
    def from_file(cls, filepath: str):
        """Load user config from JSON file"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"User config not found: {filepath}")
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        providers = {}
        for provider_name, provider_data in data.get("providers", {}).items():
            providers[provider_name] = ProviderConfig.from_dict(provider_data)
        
        # Use email as user_id
        email = data["email"]
        
        return cls(
            user_id=email,
            email=email,
            email_password=data["email_password"],
            imap_host=data.get("imap_host", "imap.gmail.com"),
            google_authenticator_secret=data.get("google_authenticator_secret", ""),
            providers=providers
        )
    
    def get_enabled_providers(self):
        """Return list of enabled provider names"""
        return [name for name, config in self.providers.items() if config.enabled]


class UserManager:
    """Manages multiple user configurations"""
    
    def __init__(self, users_dir: str = "users"):
        self.users_dir = users_dir
        self.users: Dict[str, UserConfig] = {}
        self._load_all_users()
    
    def _load_all_users(self):
        """Load all user configs from the users directory"""
        if not os.path.exists(self.users_dir):
            os.makedirs(self.users_dir)
            logger.warning(f"Created users directory: {self.users_dir}")
            return
        
        for filename in os.listdir(self.users_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.users_dir, filename)
                try:
                    user_config = UserConfig.from_file(filepath)
                    # Use email as the key
                    self.users[user_config.email] = user_config
                    logger.info(f"Loaded user config: {user_config.email} from {filename}")
                except Exception as e:
                    logger.error(f"Failed to load user config {filename}: {e}")
    
    def get_user(self, email: str) -> Optional[UserConfig]:
        """Get a specific user's config by email"""
        return self.users.get(email)
    
    def get_all_users(self) -> Dict[str, UserConfig]:
        """Get all loaded user configs"""
        return self.users
    
    def reload(self):
        """Reload all user configurations"""
        self.users.clear()
        self._load_all_users()
        logger.info(f"Reloaded {len(self.users)} user configs")
