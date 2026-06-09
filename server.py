from conf import Env
from pushnot_template import Template, Fmt
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from maglink_fetch import MaglinkFetcher



app = FastAPI()
env = Env()
maglinkFetcher = MaglinkFetcher(env=env)
html = Template(env.appjs)


@app.get("/")
async def display_maglinks(request: Request):
    return HTMLResponse(
        html.format([
            Fmt(placeholder="PAGE_TITLE", replacement=env.app_title),
            Fmt(placeholder="POLL_URL", replacement=env.poll_url),
            Fmt(placeholder="POLL_INTERVAL", replacement=str(env.poll_interval))
        ])
    )

@app.get("/notifications")
async def push_notification(request:Request):
    maglinkFetcher.poll_once()
    return JSONResponse(content=maglinkFetcher.last_20(), status_code=200)


