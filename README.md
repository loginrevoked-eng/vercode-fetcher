# OTP Publisher - Clean Refactored Version

## What Changed

### ✅ Polymorphic Provider System
- **Before**: Hard-coded for Anthropic only
- **After**: Abstract `VerificationProvider` base class with specific implementations:
  - `AnthropicProvider` (Claude)
  - `OpenAIProvider` (ChatGPT)
  - `GenericProvider` (any custom provider)
  - `ProviderFactory` for easy instantiation

### ✅ Per-User Configuration
- **Before**: Single global `configuration.json`
- **After**: `users/` directory with JSON file per user
  - Example: `users/user1.json`, `users/user2.json`
  - Each user can have multiple providers enabled
  - Easy to add/remove users without code changes

### ✅ Clean Multi-User Architecture
- **Before**: Messy nested dictionaries in `MaglinkFetcher.__init__`
- **After**: 
  - `UserManager` - loads and manages user configs
  - `Subscription` - clean dataclass linking user → provider → publisher
  - `MaglinkFetcher` - manages subscriptions per user/provider

### ✅ Stateless Template System
- **Before**: Global template mutation with `write_all()`
- **After**: `TemplateRenderer` renders per-request without side effects
  - No more file writes on every request
  - Clean separation: templates stay in `static/`

### ✅ Clean Server Routes
- **Before**: Messy template injection in `server.py`
- **After**: RESTful API structure
  - `GET /` - list all subscriptions
  - `GET /{user_id}/{provider_name}` - user's notification page
  - `GET /api/notifications/{user_id}/{provider_name}` - fetch notifications
  - `POST /api/reload` - reload configs without restart

## File Structure

```
otp_publisher/
├── users/                      # Per-user JSON configs
│   ├── user1.json
│   └── user2.json
├── providers.py                # Polymorphic provider system
├── user_manager.py             # User config management
├── service.py                  # Core IMAP/notification logic
├── subscriptions.py            # Subscription dataclass
├── static_template.py          # Stateless template renderer
├── server.py                   # Clean FastAPI server
└── static/
    ├── maglinks.html           # Template with placeholders
    └── app.js                  # Client-side polling
```

## User Config Format

`users/user1.json`:
```json
{
  "email": "user@example.com",
  "email_password": "app_password",
  "imap_host": "imap.gmail.com",
  "providers": {
    "claude": {
      "enabled": true,
      "imap_filter_query": "UNSEEN FROM \"anthropic.com\"",
      "maglink_regex": "https://auth\\.anthropic\\.com/confirm-email\\?token=[\\w-]+",
      "vercode_regex": "Your Anthropic verification code is: (\\d{6})",
      "vercode_pagemarker": "Use verification code to continue"
    },
    "chatgpt": {
      "enabled": true,
      "imap_filter_query": "UNSEEN FROM \"openai.com\"",
      "maglink_regex": "https://auth\\.openai\\.com/.*?token=[\\w-]+",
      "vercode_regex": "verification code:?\\s*(\\d{6})",
      "vercode_pagemarker": "verification code"
    }
  }
}
```

## How to Use

### 1. Add Users
Create JSON files in `users/` directory:
```bash
# Add user configs
users/alice.json
users/bob.json
```

### 2. Run Server
```bash
uvicorn server:app --host 0.0.0.0 --port 8080
```

### 3. Access Subscriptions
- Visit `http://localhost:8080/` to see all subscriptions
- Visit `http://localhost:8080/user1/claude` for specific feed
- API: `http://localhost:8080/api/notifications/user1/claude`

### 4. Add Custom Providers
```python
from providers import VerificationProvider, ProviderFactory

class MyCustomProvider(VerificationProvider):
    def extract_verification_code(self, email_content: bytes):
        # Your extraction logic
        pass
    
    def extract_magic_link(self, email_content: bytes):
        # Your extraction logic
        pass

# Register it
ProviderFactory.register_provider("mycustom", MyCustomProvider)
```

Then in user config:
```json
{
  "providers": {
    "mycustom": {
      "enabled": true,
      "imap_filter_query": "UNSEEN FROM \"example.com\"",
      ...
    }
  }
}
```

## Benefits

1. **Scalable**: Add users by dropping JSON files in `users/`
2. **Polymorphic**: Support any verification provider with regex configs
3. **Clean**: No more nested dicts, proper separation of concerns
4. **Stateless**: Templates render per-request, no file mutations
5. **Multi-tenant**: Each user gets isolated subscriptions
6. **Extensible**: Easy to add new providers without touching core code
