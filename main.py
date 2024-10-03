
from src.project import project
from src.client import Client
from discord import Intents
from argparse import ArgumentParser


def run_bot():
    client = Client(intents=Intents.all())
    client.run(project.bot_token)


def run_api():
    from src.api import app
    from uvicorn import run
    run(app, host='0.0.0.0', port=8080, forwarded_allow_ips='*')


def main():
    parser = ArgumentParser()
    parser.add_argument('mode', choices=['bot', 'api'])
    args = parser.parse_args()

    match args.mode:
        case 'bot':
            run_bot()
        case 'api':
            run_api()
        case _:
            parser.print_help()


if __name__ == '__main__':
    main()
