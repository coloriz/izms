from __future__ import annotations

import base64
from abc import ABC, abstractmethod
from pathlib import Path

from requests import Session

from .models import MailContainer


class ICommand(ABC):
    @abstractmethod
    def execute(self, mail: MailContainer):
        ...


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
