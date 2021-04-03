from requests import Session


class SessionFactory:
    __instance = None  # Singleton session instance

    @classmethod
    def instance(cls):
        if cls.__instance is None:
            cls.__instance = Session()
        return cls.__instance
