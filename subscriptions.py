"""
Subscription model - links a user to a provider with notification publisher
"""
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from service import NotiPublisher
    from user_manager import UserConfig, ProviderConfig


@dataclass
class Subscription:
    """Represents a user's subscription to a provider"""
    user_id: str
    provider_name: str
    user_config: 'UserConfig'
    provider_config: 'ProviderConfig'
    publisher: 'NotiPublisher'
    
