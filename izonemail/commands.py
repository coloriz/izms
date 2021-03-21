import base64
from abc import ABC, abstractmethod
from pathlib import Path
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup, Tag
from requests import Session, Response

from .models import MailContainer


class ICommand(ABC):
    @abstractmethod
    def execute(self, mail: MailContainer):
        ...


class InsertMailHeaderCommand(ICommand):
    """Insert mail header before mail body"""
    _header_path = Path(__file__).resolve().parent / 'assets/mail_header.min.html'
    _header_template = _header_path.read_text(encoding='utf-8')

    def execute(self, mail: MailContainer):
        header = self._header_template.format_map({
            'member_image': mail.header.member.image_url,
            'sender': mail.header.member.name,
            'received': mail.header.received.strftime('%Y/%m/%d %H:%M'),
            'recipient': mail.recipient.nickname,
            'subject': mail.header.subject,
        })
        header = BeautifulSoup(header, 'lxml').header
        mail.body.select_one('#mail-detail').insert_before(header)


class RemoveAllStyleSheetCommand(ICommand):
    """Remove all css from markup"""
    def execute(self, mail: MailContainer):
        for e in mail.body.find_all('link', attrs={'rel': 'stylesheet'}):
            e.decompose()
        for e in mail.body.find_all('style'):
            e.decompose()


class EmbedStyleSheetCommand(ICommand):
    """Embed stylesheet in markup"""
    _stylesheet_path = Path(__file__).resolve().parent / 'assets/starship.min.css'
    _stylesheet = _stylesheet_path.read_text(encoding='utf-8')

    def execute(self, mail: MailContainer):
        style = mail.body.new_tag('style')
        style.string = self._stylesheet
        mail.body.head.append(style)


class RemoveAllJSCommand(ICommand):
    """Remove all javascript blocks in markup"""
    def execute(self, mail: MailContainer):
        for e in mail.body.find_all('script'):
            e.decompose()


class FetchAllImagesCommand(ICommand):
    """Fetch all images in markup"""
    def __init__(self):
        self._s = Session()

    def execute(self, mail: MailContainer):
        for e in mail.body.find_all('img'):
            if e['src'].startswith('data:'):
                continue
            url = e['src'] if urlparse(e['src']).netloc else urljoin(mail.header.detail_url, e['src'])
            r = self._s.get(url)
            r.raise_for_status()
            self._dump(mail, e, r)

    @abstractmethod
    def _dump(self, mail: MailContainer, element: Tag, r: Response):
        pass


class ConvertAllImagesToBase64Command(FetchAllImagesCommand):
    """Convert all resources in markup to base64 encoded URI"""
    def __init__(self):
        super(ConvertAllImagesToBase64Command, self).__init__()

    def _dump(self, mail: MailContainer, element: Tag, r: Response):
        content_type = r.headers.get('Content-Type') or 'image/jpeg'
        encoded_body = base64.b64encode(r.content)
        element['src'] = f'data:{content_type};base64,{encoded_body.decode()}'


class DumpAllImagesToLocalCommand(FetchAllImagesCommand):
    """Dump all images in markup to local"""
    def __init__(self):
        super(DumpAllImagesToLocalCommand, self).__init__()
        self._base_path = Path('img')

    def _dump(self, mail: MailContainer, element: Tag, r: Response):
        # Filename is "[parent]_[filename]"
        filename = '_'.join(Path(urlparse(element['src']).path).parts[-2:])
        # Local resource path
        file = mail.path.parent / self._base_path / filename
        # Set image source relative to mail's path
        element['src'] = str(file.relative_to(mail.path.parent)).replace('\\', '/')
        # Save to local
        if file.is_file():
            return
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(r.content)
