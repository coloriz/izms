import base64
import json
from pathlib import Path

from bs4 import BeautifulSoup
from colorama import init, Fore, Style
import requests

from izonemail import IZONEMail, Mail


class MailSaver:
    def __init__(self, username, header_path='MAIL_HEADER'):
        self._username = username
        # read mail header template file
        with open(header_path) as f:
            self._header_template = f.read()

    def dump(self, fp, mail: Mail, mail_detail: bytes):
        # replace all tokens and build a soup
        header = self._header_template.replace('{{MEMBER_IMAGE}}', mail.member.image_url, 1) \
                                      .replace('{{SENDER}}', mail.member.name, 1) \
                                      .replace('{{RECEIVED}}', mail.received.strftime('%Y/%m/%d %H:%M'), 1) \
                                      .replace('{{USERNAME}}', self._username, 1) \
                                      .replace('{{MAILTITLE}}', mail.subject, 1)
        header = BeautifulSoup(header, 'lxml').header

        # parse markup of the mail and inserts header just before the main content
        markup = BeautifulSoup(mail_detail, 'lxml')
        markup.select_one('#mail-detail').insert_before(header)

        # remove unnessesary scripts
        for e in markup.find_all('script'):
            e.decompose()

        # replace all images to base64
        for e in markup.find_all('img'):
            res = requests.get(e['src'])
            content_type = res.headers['content-type']
            encoded_body = base64.b64encode(res.content)
            e['src'] = f'data:{content_type};base64,{encoded_body.decode()}'

        # save the markup to the given fp
        fp.write(str(markup))


def main():
    with open('user_settings.json') as f:
        settings = json.load(f)
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
