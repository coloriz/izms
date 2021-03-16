import json
from datetime import datetime
from pathlib import Path

from colorama import init, Fore, Style
from easydict import EasyDict

from izonemail import IZONEMail
from mailsaver import MailSaver
from utils import execute_handler as _execute_handler, datetime_to_bytes, bytes_to_datetime


def main():
    cwd = Path(__file__).resolve().parent
    # Read user settings
    settings_path = cwd / 'user_settings.json'
    if not settings_path.is_file():
        print(f"❌️ User setting '{settings_path.name}' missing!")
        exit(-1)
    settings = EasyDict(json.loads(settings_path.read_text()))

    # File containing local last mail timestamp
    head_path = cwd / 'HEAD'
    head = bytes_to_datetime(head_path.read_bytes()) if head_path.is_file() else datetime.fromtimestamp(0)
    print(f'Current local HEAD: {head.isoformat()}')
    # Mail download path
    mail_dir = Path(settings.download_path)

    def execute_handler(*args):
        finish_hook = settings.get('finish_hook')
        if finish_hook is None:
            return
        returncode = _execute_handler(finish_hook, 'IZ*ONE Mail Shelter', *args)
        if returncode != 0:
            print(f'⚠️ The return code of finish hook is non-zero ({hex(returncode)})')

    # IZ*ONE Private Mail client
    app = IZONEMail(settings.user_id, settings.access_token)

    # Check if user_id and access_token is valid
    print(f'{Fore.CYAN}==>{Fore.RESET}{Style.BRIGHT} Retrieving User Information')
    user = app.get_user()
    print(f'{user.id} / {user.nickname} / {user.gender} / {user.country_code} / {user.birthday}\n')

    # Retrieve the list of new mails
    new_mails = []
    caught_up = False
    page = 1

    while True:
        inbox = app.get_inbox(page)

        for mail in inbox:
            if mail.received <= head:
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
        return

    print(f'{len(new_mails)} new mails are available.')

    mail_saver = MailSaver(user.nickname)
    n_downloaded = 0

    try:
        # Start downloading from the oldest one
        for mail in reversed(new_mails):
            # Build file path and check if already exists
            mail_file = mail_dir / str(mail.member.id) / f'{mail.id}.html'
            if mail_file.is_file():
                print(f"⚠️ The file '{mail_file}' already exists! Skipping...")
                continue

            print(f'{Fore.GREEN}==>{Fore.RESET}{Style.BRIGHT} '
                  f'Downloading {Fore.GREEN}{mail.detail_url}')
            mail_detail = app.get_mail_detail(mail.id)

            print(f"{Fore.CYAN}==>{Fore.RESET}{Style.BRIGHT} "
                  f"Saving mail '{mail.id}' to \'{mail_file}\'")
            mail_file.parent.mkdir(parents=True, exist_ok=True)
            with mail_file.open('w', encoding='utf-8') as f:
                mail_saver.dump(f, mail, mail_detail)

            # Update HEAD
            head = mail.received
            n_downloaded += 1
    finally:
        head_path.write_bytes(datetime_to_bytes(head))
        print(f'{n_downloaded} mails downloaded.')
        if n_downloaded < len(new_mails):
            print('⚠️ Download interrupted!')

    print('💌 IZ*ONE Mail Shelter is up to date.')
    execute_handler(n_downloaded)


if __name__ == '__main__':
    init(autoreset=True)
    main()
