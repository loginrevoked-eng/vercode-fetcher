import os
from logging import getLogger, FileHandler, StreamHandler, Formatter, DEBUG, WARNING





logger = None

def setup_logging(log_file: str = "logs/empub.log", console_level: int = WARNING, level: str = "DEBUG"):
    if globals()["logger"] is not None:
        return globals()["logger"]
    if "/" in log_file or "\\" in log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    globals()["logger"] = getLogger(__name__)
    
    # Support string level parameter
    log_level = DEBUG if level == "DEBUG" else WARNING if level == "WARNING" else DEBUG
    
    globals()["logger"].setLevel(log_level)
    formatter = Formatter(
        "%(asctime)s — %(name)s — %(levelname)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = FileHandler(log_file)
    file_handler.setLevel(DEBUG)
    file_handler.setFormatter(formatter)
    console_handler = StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    globals()["logger"].addHandler(file_handler)
    globals()["logger"].addHandler(console_handler)

    return globals()["logger"]

def panic(msg:str="PANIC!", tag:str="PANIC!", code:int=1):
    globals()["logger"].error(
        f":( {tag}: {msg}"
    )
    exit(code)


