import json
from pathlib import Path

from colorama import init, Fore, Style

from izonemail import IZONEMail
from mailsaver import MailSaver


def main():
    # read user settings
    settings = json.loads((Path(__file__).resolve().parent / 'user_settings.json').read_text())
    # directory in which mails are saved
    mail_dir = Path(settings['download_path'])

    # select the most recent mail id
    recent_pure_mail_id = -1
    for mail in mail_dir.glob('*/*.html'):
        # in case of birthday mail, just skip it
        if mail.stem[0] == 'b':
            continue
        pure_mail_id = int(mail.stem[1:])
        if recent_pure_mail_id < pure_mail_id:
            recent_pure_mail_id = pure_mail_id
    print(f'💌 An ID of the most recent mail is {recent_pure_mail_id if recent_pure_mail_id != -1 else "None"}')

    app = IZONEMail(settings['user_id'], settings['access_token'])

    # Let's take a dry run
    inbox = app.get_inbox()
    if inbox.mails and inbox.mails[0].pure_id > recent_pure_mail_id:
        print('New mails are available in your inbox.')
    else:
        print('Already up-to-date.')
        return

    print(f'{Fore.CYAN}==>{Fore.RESET}{Style.BRIGHT} Retrieving User Information')
    user = app.get_user()
    print(f'{user.nickname} / {user.gender} / {user.country_code} / {user.birthday}\n')

    mail_saver = MailSaver(user.nickname)
    num_retrieved_mail = 0

    caught_up = False
    page = 1

    while True:
        inbox = app.get_inbox(page)

        for mail in inbox.mails:
            if mail.pure_id <= recent_pure_mail_id:
                caught_up = True
                break
            # we still didn't catch up
            # build file path and check if already exists
            mail_file = mail_dir / str(mail.member.id) / f'{mail.id}.html'
            if mail_file.is_file():
                print(f'⚠️ The file \'{mail_file.resolve()}\' already exists! Skipping...')
                continue

            # download mail detail and save it
            print(f'{Fore.GREEN}==>{Fore.RESET}{Style.BRIGHT} '
                  f'Downloading a new mail{Fore.GREEN} {mail.id}')
            print(f'{mail.id}: {mail.member.name} / {mail.subject} / {mail.received}')
            mail_detail = app.get_mail_detail(mail.id)

            print(f'{Fore.CYAN}==>{Fore.RESET}{Style.BRIGHT} '
                  f'Saving Mail \'{mail.id}\' to \'{mail_file.resolve()}\'.')
            mail_file.parent.mkdir(parents=True, exist_ok=True)
            with mail_file.open('w') as f:
                mail_saver.dump(f, mail, mail_detail)
            # increase retrieved mail counter
            num_retrieved_mail += 1

        # if we caught up or this inbox was the last one, break the loop
        if caught_up or not inbox.has_next_page:
            break

        page += 1

    if num_retrieved_mail > 0:
        print(f'Downloaded {num_retrieved_mail} mail{"" if num_retrieved_mail == 1 else "s"} from the mail server')
    print('💌 IZ*ONE Mail Shelter is up to date.')


if __name__ == '__main__':
    init(autoreset=True)
    main()
