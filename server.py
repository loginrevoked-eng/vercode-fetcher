"""
Clean FastAPI server with per-user, per-provider subscriptions
"""
from conf import Config
from fastapi import FastAPI, HTTPException
from service import MaglinkFetcher
from static_template import TemplateRenderer
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse
from logger import setup_logging

logger = setup_logging("logs/server.log", level="INFO")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Load global config (non-user stuff only) - skip argv to avoid conflicts with uvicorn
env = Config().from_json("configuration.json").from_env()

# Initialize multi-user fetcher
maglinkFetcher = MaglinkFetcher(users_dir="users", global_config=env)

# Initialize stateless template renderer
template_renderer = TemplateRenderer(html_template_path="static/maglinks.html")


@app.get("/")
async def root():
    """Root endpoint - show list of available subscriptions"""
    html = """
    <html>
    <head>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 40px; background: #f5f5f5; }
            h1 { color: #202124; }
            h2 { color: #5f6368; font-size: 18px; margin-top: 32px; }
            ul { list-style: none; padding: 0; }
            li { margin: 8px 0; }
            a { color: #1a73e8; text-decoration: none; padding: 8px 12px; display: inline-block; }
            a:hover { background: #e8f0fe; border-radius: 4px; }
        </style>
    </head>
    <body>
        <h1>OTP Publisher</h1>
    """
    
    for email, providers in maglinkFetcher.subscriptions.items():
        username = email.split('@')[0]
        html += f"<h2>{email}</h2><ul>"
        
        # Add Google Authenticator link if configured
        user_config = maglinkFetcher.user_manager.get_user(email)
        if user_config and user_config.google_authenticator_secret:
            html += f'<li>🔑 <a href="/{username}/google-oauth">Google Authenticator</a></li>'
        
        # Add provider links
        for provider_name in providers.keys():
            html += f'<li>📧 <a href="/{username}/{provider_name}">{provider_name.title()}</a></li>'
        
        html += "</ul>"
    
    html += "</body></html>"
    return HTMLResponse(html)


@app.get("/{username}/google-oauth")
async def google_oauth(username: str):
    """Generate realtime Google Authenticator OTP"""
    email = f"{username}@gmail.com"
    user_config = maglinkFetcher.user_manager.get_user(email)
    
    if not user_config:
        raise HTTPException(status_code=404, detail=f"User not found: {email}")
    
    if not user_config.google_authenticator_secret:
        raise HTTPException(status_code=400, detail=f"No Google Authenticator secret configured for {email}")
    
    try:
        import pyotp
        
        # Clean and format the secret key
        secret_key = user_config.google_authenticator_secret.replace(" ", "").upper()
        totp = pyotp.TOTP(secret_key)
        current_otp = totp.now()
        
        # Calculate time remaining
        import time
        remaining_seconds = 30 - (int(time.time()) % 30)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Google Authenticator - {username}</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    background: #f5f5f5;
                }}
                .container {{
                    background: white;
                    border-radius: 16px;
                    padding: 48px;
                    box-shadow: 0 4px 16px rgba(0,0,0,0.1);
                    text-align: center;
                }}
                .email {{
                    color: #5f6368;
                    font-size: 14px;
                    margin-bottom: 24px;
                }}
                .otp {{
                    font-size: 56px;
                    font-weight: 600;
                    letter-spacing: 8px;
                    color: #1a73e8;
                    font-family: 'Courier New', monospace;
                    margin: 24px 0;
                }}
                .timer {{
                    font-size: 18px;
                    color: #5f6368;
                    margin-top: 16px;
                }}
                .progress {{
                    width: 100%;
                    height: 4px;
                    background: #e8eaed;
                    border-radius: 2px;
                    margin-top: 24px;
                    overflow: hidden;
                }}
                .progress-bar {{
                    height: 100%;
                    background: #1a73e8;
                    width: 100%;
                    transition: width 1s linear;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="email">{email}</div>
                <h1>Google Authenticator</h1>
                <div class="otp" id="otp">{current_otp}</div>
                <div class="timer" id="timer">Refreshes in {remaining_seconds} seconds</div>
                <div class="progress">
                    <div class="progress-bar" id="progress"></div>
                </div>
            </div>
            <script>
                let remaining = {remaining_seconds};
                
                function updateTimer() {{
                    document.getElementById('timer').textContent = `Refreshes in ${{remaining}} seconds`;
                    const percent = (remaining / 30) * 100;
                    document.getElementById('progress').style.width = percent + '%';
                    remaining--;
                }}
                
                function fetchNewOtp() {{
                    fetch(window.location.href)
                        .then(r => r.text())
                        .then(html => {{
                            const parser = new DOMParser();
                            const doc = parser.parseFromString(html, 'text/html');
                            const newOtp = doc.getElementById('otp').textContent;
                            const newRemaining = parseInt(doc.getElementById('timer').textContent.match(/\\d+/)[0]);
                            
                            document.getElementById('otp').textContent = newOtp;
                            remaining = newRemaining;
                        }});
                }}
                
                // Update timer every second
                setInterval(updateTimer, 1000);
                
                // Poll for new OTP every 5 seconds
                setInterval(fetchNewOtp, 5000);
            </script>
        </body>
        </html>
        """
        return HTMLResponse(html)
        
    except ImportError:
        raise HTTPException(status_code=500, detail="pyotp library not installed. Run: pip install pyotp")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating OTP: {str(e)}")


@app.get("/{username}/{provider_name}")
async def user_provider_page(username: str, provider_name: str):
    """Render the notification page for a specific username/provider"""
    email = f"{username}@gmail.com"
    subscription = maglinkFetcher.get_subscription(email, provider_name)
    
    if not subscription:
        raise HTTPException(status_code=404, detail=f"Subscription not found: {email}/{provider_name}")
    
    # Return static HTML - JS will extract username/provider from URL
    return HTMLResponse(template_renderer.html_template)


@app.get("/api/notifications/{username}/{provider_name}")
async def get_notifications(username: str, provider_name: str):
    """API endpoint to fetch notifications for a specific username/provider"""
    email = f"{username}@gmail.com"
    print(f">>> API request for username={repr(username)}, email={repr(email)}, provider={repr(provider_name)}")
    print(f">>> Available subscriptions: {list(maglinkFetcher.subscriptions.keys())}")
    
    subscription = maglinkFetcher.get_subscription(email, provider_name)
    
    if not subscription:
        print(f">>> Subscription not found!")
        raise HTTPException(status_code=404, detail=f"Subscription not found: {email}/{provider_name}")
    
    try:
        feed = maglinkFetcher.get_feed(email, provider_name)
        
        # Convert notifications to JSON-serializable format
        notifications = [
            {
                "title": noti.title,
                "detail": noti.detail,
                "timestamp": noti.timestamp,
                "read": noti.read
            }
            for noti in feed
        ]
        
        print(f">>> Returning {len(notifications)} notifications")
        return JSONResponse(content=notifications, status_code=200)
    except Exception as e:
        print(f">>> Exception: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reload")
async def reload_configs():
    """Reload user configurations"""
    try:
        maglinkFetcher.user_manager.reload()
        maglinkFetcher._initialize_subscriptions()
        template_renderer.reload_template()
        return JSONResponse({"status": "success", "message": "Configurations reloaded"})
    except Exception as e:
        logger.error(f"Failed to reload configs: {e}")
        raise HTTPException(status_code=500, detail=str(e))





