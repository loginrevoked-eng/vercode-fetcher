from datetime import datetime
from dataclasses import dataclass


@dataclass
class Notification:
    title: str
    timestamp: str
    detail: str
    read: bool

    @classmethod
    def new(cls, title: str = "Nothing New Yet", detail: str = "No new notifications found"):
        return cls(
            title=title, timestamp=datetime.now().isoformat(),
            detail=detail, read=False
        )

    def mark_read(self):
        self.read = True
        return self
    
    def is_unread(self):
        return not self.read