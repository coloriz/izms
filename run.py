import json
import pickle
import sys
from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path

from colorama import init, Fore, Style
from easydict import EasyDict
from tqdm import tqdm

from izonemail import (
    MailComposer,
    InsertMailHeaderCommand,
    RemoveAllJSCommand,
    RemoveAllStyleSheetCommand,
    EmbedStyleSheetCommand,
    DumpStyleSheetToLocalCommand,
    ConvertAllImagesToBase64Command,
    DumpAllImagesToLocalCommand,
)
from izonemail import Profile, IZONEMail
from options import Options, Option
from utils import execute_handler as _execute_handler, datetime_to_bytes, bytes_to_datetime


def main():
    cwd = Path(__file__).resolve().parent
    default_config_path = cwd / 'config.json'
    parser = ArgumentParser(prog='IZ*ONE Mail Shelter')
    parser.add_argument('-c', '--config', default=default_config_path, type=Path, metavar='<file>',
                        help='Specify a JSON-format text file to read user configurations from.')
    args = parser.parse_args()

    # Parse user config
    config_path = args.config
    print(f'{Fore.YELLOW}==>{Fore.RESET}{Style.BRIGHT} Parsing configuration')
    # Validate config
    root = Options('root')
    root.add(Option('mail_path', required=True))
    root.add(Option('embed_css', default=False, type=bool))
    root.add(Option('css_path', default='../css'))
    root.add(Option('image_to_base64', default=False, type=bool))
    root.add(Option('image_path', default='img'))
    root.add(Option('timeout', default=5, type=(int, float), validator=lambda t: t >= 0))
    root.add(Option('max_retries', default=3, type=int, validator=lambda i: i >= 0))
    root.add(Option('finish_hook', validator=lambda s: len(s) > 0))
    profile = Options('profile', required=True)
    for k in Profile.valid_keys():
        profile.add(Option(k, required=Profile.is_required_key(k)))
    root.add(profile)

    try:
        config = EasyDict(json.loads(config_path.read_text(encoding='utf-8')))
        root.parse_options(config)
    except FileNotFoundError as e:
        print(f"❌️ Configuration file '{e.filename}' missing!")
        return -1
    except (KeyError, TypeError, ValueError) as e:
        print(f"❌️ {e}")
        return -2

    # Print parsed config
    print(json.dumps(config, indent=4))

    # File containing local last mail timestamp
    head_path = cwd / 'HEAD'
    head = bytes_to_datetime(head_path.read_bytes()) if head_path.is_file() else datetime.fromtimestamp(0)
    print(f'📢 {Fore.CYAN}{Style.BRIGHT}HEAD -> {Fore.GREEN}{head.isoformat()}')
    # Index file
    index_path = cwd / 'INDEX'
    index = pickle.loads(index_path.read_bytes()) if index_path.is_file() else set()

    def execute_handler(*args):
        finish_hook = config.finish_hook
        if finish_hook is None:
            return
        returncode = _execute_handler(finish_hook, 'IZ*ONE Mail Shelter', *args)
        if returncode != 0:
            print(f'⚠️ The return code of finish hook is non-zero ({hex(returncode)})')

    # IZ*ONE Private Mail client
    app = IZONEMail(Profile({k: v for k, v in config.profile.items() if v}),
                    timeout=config.timeout, max_retries=config.max_retries)

    # Check if profile is valid
    print(f'\n{Fore.BLUE}==>{Fore.RESET}{Style.BRIGHT} Retrieving user information')
    user = app.get_user()
    print(f'{user.id} / {user.nickname} / {user.gender} / {user.country_code} / {user.birthday}')

    # Retrieve the list of new mails
    print(f'\n{Fore.MAGENTA}==>{Fore.RESET}{Style.BRIGHT} Retrieving new mails from inbox')
    new_mails = []
    caught_up = False
    page = 1

    while True:
        inbox = app.get_inbox(page)
        for mail in inbox:
            if mail.id in index:
                caught_up = True
                break
            print(f'💌 Found new mail {mail.id}: {mail.member.name} / {mail.subject} / {mail.received}')
            new_mails.append(mail)
        # If we caught up or this inbox was the last one, break the loop
        if caught_up or not inbox.has_next_page:
            break
        page += 1

    if not new_mails:
        print('Already up-to-date.')
        execute_handler(0)
        return 0

    n_total = len(new_mails)
    print(f'{n_total} new mails are available.')

    # Start downloading mails
    print(f'\n{Fore.GREEN}==>{Fore.RESET}{Style.BRIGHT} Downloading new mails')
    # Create mail composer
    mail_composer = MailComposer()
    mail_composer += InsertMailHeaderCommand()
    mail_composer += RemoveAllJSCommand()
    mail_composer += RemoveAllStyleSheetCommand()
    mail_composer += EmbedStyleSheetCommand() if config.embed_css else DumpStyleSheetToLocalCommand(config.css_path)
    mail_composer += ConvertAllImagesToBase64Command() if config.image_to_base64 else DumpAllImagesToLocalCommand(config.image_path)

    n_downloaded = 0
    n_skipped = 0

    try:
        # Start from the oldest one
        pbar = tqdm(reversed(new_mails), total=n_total)
        for mail in pbar:
            pbar.set_description(f'Processing {mail.id}')
            # Build file path and check if already exists
            mail_path = config.mail_path.format_map({
                'member_id': mail.member.id,
                'member_name': mail.member.name,
                'mail_id': mail.id,
                'received': mail.received,
                'subject': mail.subject,
            })
            mail_file = Path(mail_path)
            if mail_file.is_file():
                tqdm.write(f"⚠️ File '{mail_file}' already exists! Skipping...")
                head = mail.received
                index.add(mail.id)
                n_skipped += 1
                continue
            # Fetch mail detail
            mail_detail = app.get_mail_detail(mail)
            # Compose mail content
            content = mail_composer(user, mail, mail_detail, mail_file)
            # Save to specified path
            mail_file.parent.mkdir(parents=True, exist_ok=True)
            mail_file.write_text(content, encoding='utf-8')
            # Update HEAD
            head = mail.received
            # Update INDEX
            index.add(mail.id)
            n_downloaded += 1
    finally:
        print(f'\n{Fore.CYAN}==>{Fore.RESET}{Style.BRIGHT} Summary')
        print(f'Total: {n_total} / Downloaded: {n_downloaded} / Skipped: {n_skipped}')
        head_path.write_bytes(datetime_to_bytes(head))
        index_path.write_bytes(pickle.dumps(index))
        print(f'📢 {Fore.CYAN}{Style.BRIGHT}HEAD -> {Fore.GREEN}{head.isoformat()}')

    print('\n💌 IZ*ONE Mail Shelter is up to date.')
    execute_handler(n_downloaded)
    return 0


if __name__ == '__main__':
    init(autoreset=True)
    sys.exit(main())
