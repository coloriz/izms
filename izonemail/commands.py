from abc import ABC, abstractmethod
from functools import lru_cache
from os import PathLike
from os.path import relpath
from pathlib import Path
from typing import Union
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup

from .__version__ import __title__, __version__
from .factory import SessionFactory
from .models import Artifact, ComposerPayload
from .utils import naive_join, response_to_base64, as_posix


class ICommand(ABC):
    @abstractmethod
    def execute(self, mail: ComposerPayload):
        ...


class InsertMailHeaderCommand(ICommand):
    """Insert mail header before mail body"""
    _header_path = Path(__file__).resolve().parent / 'assets/mail_header.min.html'
    _header_template = _header_path.read_text(encoding='utf-8')

    def __init__(self, profile_image_root: Union[str, PathLike, None] = '/'):
        self._s = SessionFactory.instance()
        self._profile_image_root = profile_image_root
        if self._profile_image_root is not None:
            self._profile_image_root = Path(self._profile_image_root)

    @lru_cache
    def _get(self, url, **kwargs):
        r = self._s.get(url, **kwargs)
        r.raise_for_status()
        return r

    def execute(self, mail: ComposerPayload):
        r = self._get(mail.header.member.image_url)

        if self._profile_image_root:
            path = Path(urlparse(mail.header.member.image_url).path)
            path = naive_join(self._profile_image_root, path)
            mail.artifacts.append(Artifact(path, r.content))
            url = as_posix(relpath(path, mail.path.parent))
        else:
            url = response_to_base64(r)

        header = self._header_template.format_map({
            'member_image': url,
            'sender': mail.header.member.name,
            'received': mail.header.received.strftime('%Y/%m/%d %H:%M'),
            'recipient': mail.recipient.nickname,
            'subject': mail.header.subject,
        })
        header = BeautifulSoup(header, 'lxml').header
        mail.body.select_one('#mail-detail').insert_before(header)


class RemoveAllMetaTagsCommand(ICommand):
    """Remove all meta tag from markup"""
    def execute(self, mail: ComposerPayload):
        for e in mail.body.find_all('meta'):
            e.decompose()


class InsertAppMetadataCommand(ICommand):
    """Insert charset, viewport, app metadata"""
    def execute(self, mail: ComposerPayload):
        app_meta = {
            'name': 'application-name',
            'content': __title__,
            'data-version': __version__,
            'data-member-id': f'{mail.header.member.id}',
            'data-id': mail.header.id,
            'data-subject': mail.header.subject,
            'data-content': mail.header.content,
            'data-received': mail.header.received.isoformat(' '),
        }
        meta_tags = [
            mail.body.new_tag('meta', attrs={'charset': 'utf-8'}),
            mail.body.new_tag('meta', attrs=app_meta),
            mail.body.new_tag('meta', attrs={
                'name': 'viewport',
                'content': 'width=device-width, initial-scale=1, minimum-scale=1, maximum-scale=1'
            }),
        ]
        for tag in meta_tags:
            mail.body.head.append(tag)


class RemoveAllStyleSheetCommand(ICommand):
    """Remove all css from markup"""
    def execute(self, mail: ComposerPayload):
        for e in mail.body.find_all('link', attrs={'rel': 'stylesheet'}):
            e.decompose()
        for e in mail.body.find_all('style'):
            e.decompose()


class DumpStyleSheetCommand(ICommand):
    """Dump stylesheet to local or embed in markup"""
    _stylesheet_path = Path(__file__).resolve().parent / 'assets/starship.min.css'
    _stylesheet = _stylesheet_path.read_text(encoding='utf-8')

    def __init__(self, css_root: Union[str, PathLike, None] = '/css'):
        self._css_root = css_root
        if self._css_root is not None:
            self._css_root = Path(self._css_root)

    def execute(self, mail: ComposerPayload):
        if self._css_root:
            path = self._css_root / self._stylesheet_path.name
            mail.artifacts.append(Artifact(path, self._stylesheet.encode('utf-8')))
            url = as_posix(relpath(path, mail.path.parent))

            tag = mail.body.new_tag('link')
            tag['rel'] = 'stylesheet'
            tag['href'] = url
        else:
            tag = mail.body.new_tag('style')
            tag.string = self._stylesheet

        mail.body.head.append(tag)


class RemoveAllJSCommand(ICommand):
    """Remove all javascript blocks in markup"""
    def execute(self, mail: ComposerPayload):
        for e in mail.body.find_all('script'):
            e.decompose()


class DumpAllImagesCommand(ICommand):
    """Fetch all images in markup"""
    def __init__(self, img_root: Union[str, PathLike, None] = '/img'):
        self._s = SessionFactory.instance()
        self._img_root = img_root
        if self._img_root is not None:
            self._img_root = Path(self._img_root)

    def execute(self, mail: ComposerPayload):
        for e in mail.body.find_all('img'):
            if e['src'].startswith('data:'):
                continue
            url = e['src'] if urlparse(e['src']).netloc else urljoin(mail.header.detail_url, e['src'])
            r = self._s.get(url)
            r.raise_for_status()

            if self._img_root:
                parts = urlparse(url).path.split('/')
                path = naive_join(self._img_root, Path(*parts[-3:]))
                mail.artifacts.append(Artifact(path, r.content))
                url = as_posix(relpath(path, mail.path.parent))
            else:
                url = response_to_base64(r)

            e['src'] = url


class DumpMailMarkupCommand(ICommand):
    def execute(self, mail: ComposerPayload):
        mail.artifacts.append(Artifact(mail.path, mail.body.encode()))
