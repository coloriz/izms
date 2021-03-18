from __future__ import annotations

import base64
from abc import ABC, abstractmethod
from pathlib import Path

from bs4 import BeautifulSoup
from requests import Session

from .models import MailContainer


class ICommand(ABC):
    @abstractmethod
    def execute(self, mail: MailContainer):
        ...


class InsertMailHeaderCommand(ICommand):
    """Insert mail header before mail body"""
    _header_path = Path(__file__).resolve().parent / 'assets/mail_header.html'
    _header_template = _header_path.read_text()

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
    _stylesheet_path = Path(__file__).resolve().parent / 'assets/starship.css'
    _stylesheet = _stylesheet_path.read_text()

    def execute(self, mail: MailContainer):
        style = mail.body.new_tag('style')
        style.string = self._stylesheet
        mail.body.head.append(style)


class RemoveAllJSCommand(ICommand):
    """Remove all javascript blocks in markup"""
    def execute(self, mail: MailContainer):
        for e in mail.body.find_all('script'):
            e.decompose()


class ConvertImagesToBase64Command(ICommand):
    """Convert all images in markup to base64 encoded URI"""
    def __init__(self, session: Session):
        self._s = session

    def execute(self, mail: MailContainer):
        for e in mail.body.find_all('img'):
            r = self._s.get(e['src'])
            r.raise_for_status()
            content_type = r.headers.get('Content-Type') or 'image/jpeg'
            encoded_body = base64.b64encode(r.content)
            e['src'] = f'data:{content_type};base64,{encoded_body.decode()}'
