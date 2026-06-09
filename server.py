from conf import Env
from pushnot_template import Template, Fmt
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from maglink_fetch import MaglinkFetcher



app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
env = Env().from_toml("configuration.toml")
maglinkFetcher = MaglinkFetcher(env=env)
template = Template(js=env.appjs, html=env.home_page)
template.format([
    Fmt(placeholder="POLL_INTERVAL", replacement=str(env.poll_interval)),
    Fmt(placeholder="POLL_URL", replacement=env.poll_url),
    Fmt(placeholder="PAGE_TITLE", replacement=env.app_title),
    Fmt(placeholder="EMAIL", replacement=env.email)
])
template.write_all()


@app.get("/")
async def display_maglinks(request: Request):
    return HTMLResponse(template.html())

@app.get("/notifications")
async def push_notification(request:Request):
    maglinkFetcher.poll_once()
    return JSONResponse(content=maglinkFetcher.last_20(), status_code=200)


