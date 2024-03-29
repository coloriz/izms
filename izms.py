import json
import pickle
import sys
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from colorama import init, Fore, Style
from easydict import EasyDict
from tqdm import tqdm

from adapters import TimeoutHTTPAdapter
from izonemail import (
    MailComposer,
    InsertMailHeader,
    RemoveAllMetaTags,
    InsertAppMetadata,
    RemoveAllStyleSheet,
    DumpStyleSheet,
    RemoveAllJS,
    DumpAllImages,
    DumpMailMarkup,
)
from izonemail import Profile, IZONEMail, SessionFactory, PolicyFactory
from options import Options, Option
from utils import (
    execute_handler as _execute_handler,
    datetime_to_bytes,
    bytes_to_datetime,
    is_ge_zero,
    is_gt_zero,
    is_abspath,
    is_abspath_or_none,
)

__title__ = 'IZ*ONE Mail Shelter'
__url__ = 'https://github.com/coloriz/izone-mail-shelter'
__version__ = '2021.05.29'
__author__ = 'coloriz'
__author_email__ = 'nunu3041@gmail.com'
__license__ = 'MIT'
__copyright__ = 'Copyright 2021 coloriz'


def main():
    cwd = Path(sys.argv[0]).resolve().parent
    default_config_path = cwd / 'config.json'
    parser = ArgumentParser(description=f'{__title__} v{__version__} by {__author__}')
    parser.add_argument('-c', '--config', default=default_config_path, type=Path, metavar='<file>',
                        help='Specify a JSON-format text file to read user configurations from.')
    args = parser.parse_args()

    print(f'{__title__} version {__version__} ({__url__})\n')
    # Parse user config
    config_path = args.config
    print(f'{Fore.YELLOW}==>{Fore.RESET}{Style.BRIGHT} Parsing configuration')
    # Validate config
    root = Options('root')
    root.add(Option('bundle_id', default='com.ca-smart.izonemail'))
    root.add(Option('destination', default='incoming'))
    root.add(Option('mail_path', required=True, validator=is_abspath))
    root.add(Option('profile_image_path', default='/', type=(str, type(None)), validator=is_abspath_or_none))
    root.add(Option('css_path', default='/css', type=(str, type(None)), validator=is_abspath_or_none))
    root.add(Option('image_path', default='/img', type=(str, type(None)), validator=is_abspath_or_none))
    root.add(Option('timeout', default=5, type=(int, float), validator=is_ge_zero))
    root.add(Option('max_retries', default=3, type=int, validator=is_ge_zero))
    root.add(Option('max_workers', default=8, type=int, validator=is_gt_zero))
    root.add(Option('head', default='HEAD'))
    root.add(Option('index', default='INDEX'))
    root.add(Option('finish_hook'))
    profile = Options('profile', required=True)
    for k in Profile.valid_keys():
        profile.add(Option(k, required=Profile.is_required_key(k)))
    root.add(profile)

    try:
        config = EasyDict(json.loads(config_path.read_text('utf-8')))
        root.parse_options(config)
        policy = PolicyFactory.get(config.bundle_id)
    except FileNotFoundError as e:
        print(f"❌️ File '{e.filename}' missing!", file=sys.stderr)
        return -1
    except (KeyError, TypeError, ValueError) as e:
        print(f"❌️ {e}", file=sys.stderr)
        return -2

    # Print parsed config
    print(json.dumps(config, indent=4))

    # File containing local last mail timestamp
    head_path = cwd / config.head
    head = bytes_to_datetime(head_path.read_bytes()) if head_path.is_file() else policy.genesis
    print(f'📢 {Fore.CYAN}{Style.BRIGHT}HEAD -> {Fore.GREEN}{head.isoformat()}')
    # Index file
    index_path = cwd / config.index
    index = pickle.loads(index_path.read_bytes()) if index_path.is_file() else set()

    def execute_handler(*args):
        finish_hook = config.finish_hook
        if finish_hook is None:
            return
        returncode = _execute_handler(finish_hook, __title__, *args)
        if returncode != 0:
            print(f'⚠️ The return code of finish hook is non-zero ({hex(returncode)})', file=sys.stderr)

    # Global session options
    s = SessionFactory.instance()
    adapter = TimeoutHTTPAdapter(timeout=config.timeout, max_retries=config.max_retries)
    s.mount('https://', adapter)
    s.mount('http://', adapter)
    # IZ*ONE Private Mail client
    app = IZONEMail(policy.api_host, Profile({k: v for k, v in config.profile.items() if v}))

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

    # Reverse order (from the oldest)
    new_mails = new_mails[::-1]
    n_total = len(new_mails)
    print(f'{n_total} new mails are available.')

    # Start downloading mails
    print(f'\n{Fore.GREEN}==>{Fore.RESET}{Style.BRIGHT} Downloading new mails')
    # Create mail composer
    mail_composer = MailComposer(config.destination, config.mail_path)
    mail_composer += RemoveAllMetaTags()
    mail_composer += RemoveAllJS()
    mail_composer += RemoveAllStyleSheet()
    mail_composer += InsertAppMetadata()
    mail_composer += DumpStyleSheet(policy.css, config.css_path)
    mail_composer += DumpAllImages(config.image_path)
    mail_composer += InsertMailHeader(policy.mail_header, config.profile_image_path)
    mail_composer += DumpMailMarkup()

    downloaded_mails = set()

    def process_mail(mail):
        mail_detail = app.get_mail_detail(mail)
        mail_composer.compose(user, mail, mail_detail)
        return mail

    executor = ThreadPoolExecutor(max_workers=config.max_workers)
    futures = [executor.submit(process_mail, mail) for mail in new_mails]
    pbar = tqdm(as_completed(futures), total=n_total)

    try:
        for future in pbar:
            mail = future.result()
            pbar.set_description(f'Processing {mail.id}')
            downloaded_mails.add(mail)
    finally:
        executor.shutdown(wait=True, cancel_futures=True)
        # Discard any mail that has been downloaded after error occured
        for mail in new_mails:
            if mail not in downloaded_mails:
                break
            head = mail.received
            index.add(mail.id)
        head_path.write_bytes(datetime_to_bytes(head))
        index_path.write_bytes(pickle.dumps(index))
        print(f'\n{Fore.CYAN}==>{Fore.RESET}{Style.BRIGHT} Summary')
        print(f'Total: {n_total} / Downloaded: {len(downloaded_mails)}')
        print(f'📢 {Fore.CYAN}{Style.BRIGHT}HEAD -> {Fore.GREEN}{head.isoformat()}')

    print(f'\n🎉 {__title__} is up to date.')
    execute_handler(len(downloaded_mails))
    return 0


if __name__ == '__main__':
    init(autoreset=True)
    sys.exit(main())
