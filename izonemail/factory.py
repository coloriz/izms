import json
from datetime import datetime
from pathlib import Path

from requests import Session

from .models import Policy


class SessionFactory:
    __instance = None  # Singleton session instance

    @classmethod
    def instance(cls):
        if cls.__instance is None:
            cls.__instance = Session()
        return cls.__instance


class AssetFactory:
    _asset_path = Path(__file__).resolve().parent / 'assets'
    _custom_assets = {}

    @classmethod
    def register(cls, key: str, value: bytes):
        cls._custom_assets[key] = value

    @classmethod
    def get(cls, key: str) -> bytes:
        path = cls._asset_path / key
        if path.is_file():
            asset = path.read_bytes()
        elif key in cls._custom_assets:
            asset = cls._custom_assets[key]
        else:
            raise FileNotFoundError(f'No such asset: {repr(key)}')
        return asset


class PolicyFactory:
    _policies = json.loads(AssetFactory.get('policy.json').decode('utf-8'))

    @classmethod
    def get(cls, bundle_id: str) -> Policy:
        for p in cls._policies:
            if p['bundle_id'] == bundle_id:
                break
        else:
            raise ValueError(f'Unknown bundle id: {repr(bundle_id)}. '
                             f'possible values: {[p["bundle_id"] for p in cls._policies]}')

        genesis = datetime.fromisoformat(p['genesis'])
        return Policy(p['bundle_id'], p['api_host'], p['app_host'], p['mail_header'], p['css'], genesis)
