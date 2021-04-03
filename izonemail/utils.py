import base64
import re
from os import sep, PathLike
from pathlib import Path
from typing import Union

from requests import Response


def naive_join(*args: Path):
    """Join multiple paths ignoring its root"""
    parts = list(args[0].parts)
    for a in args[1:]:
        parts += a.parts[1:] if a.root else a.parts
    return Path(*parts)


def response_to_base64(r: Response, default_mimetype: str = 'image/jpeg'):
    content_type = r.headers.get('Content-Type') or default_mimetype
    encoded_body = base64.b64encode(r.content)
    return f'data:{content_type};base64,{encoded_body.decode()}'


def as_posix(p: Union[str, PathLike]):
    return str(p).replace(sep, '/')


# Set up regular expressions
re_fc = re.compile(r'[<>:\"/\\|?*]')  # Forbidden printable ASCII characters in file path


def slugify(s):
    s = re_fc.sub('_', s)
    return s.strip()
