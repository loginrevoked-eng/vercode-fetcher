import subprocess
from conf import Env
from shutil import which
from argparse import ArgumentParser
from colorama import Fore, Style, init
from subprocess import Popen, CREATE_NEW_CONSOLE
from importlib.metadata import metadata, PackageNotFoundError




INDENT = 2
FILE = "server.py"
OBJECT = "app"
DEPLOYED = False




def prompt(stmt: str, question: str = "") -> bool:
    print(f"{' ' * INDENT}{stmt}")
    c = input(question).strip().lower()
    return c in ("y", "yes")


def install_uvicorn() -> None:
    if prompt("Uvicorn not found.", question="Do you want to install it? (y/n) "):
        try:
            subprocess.run(["pip", "install", "uvicorn"], check=True)
        except Exception as e:
            print(f"Error installing uvicorn: {e}")
            exit(1)
    else:
        print(f"{' ' * INDENT}{Fore.RED}Aborting...{Style.RESET_ALL}")
        exit(1)


def resolve_uvicorn_program() -> list[str]:
    if which("uvicorn"):
        return ["uvicorn"]
    if DEPLOYED:
        raise RuntimeError("Uvicorn not found and deployment mode is enabled")
    try:
        metadata("uvicorn")
        return ["python", "-m", "uvicorn"]
    except PackageNotFoundError:
        install_uvicorn()
        return ["uvicorn"]

def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--config", "-cfg", default="configuration.toml")
    parser.add_argument("--silent", "-s", action="store_true")
    args = parser.parse_args()

    env = Env().from_toml(args.config).from_env().from_argv()
    globals()["DEPLOYED"] = env.is_deployed
    program = resolve_uvicorn_program()
    command = program + [f"{FILE[:-3]}:{OBJECT}", "--host", env.host, "--port", str(env.port)]

    if env.is_deployed:proc = Popen(command)
    else:proc = Popen(["cmd", "/k"] + command, creationflags=CREATE_NEW_CONSOLE)

    if not args.silent:
        init(autoreset=True)
        print(f"{' ' * INDENT}Server started on {env.host}:{env.port} with pid: {proc.pid}")
        
if __name__ == "__main__":
    main()