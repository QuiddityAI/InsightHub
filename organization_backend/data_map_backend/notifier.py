import os
import requests
import logging


class BaseNotifier:
    def __init__(self, name) -> None:
        self.name = name

    def _send(self, text):
        raise NotImplementedError()

    def send(self, kind, message):
        prfx = kind + ": \n"
        if self.name:
            prfx += self.name + ", "
        try:
            self._send(prfx + message)
        except Exception as e:
            logging.warn(f"Can't send notification, {repr(e)}")

    def info(self, message):
        self.send("Info", message)

    def warning(self, message):
        self.send("Warning", message)

    def error(self, message):
        self.send("Error", message)


class TgNotifier(BaseNotifier):
    def __init__(self, token=None, chat_id=None, name="") -> None:
        super().__init__(name)
        self.token = token
        self.chat_id = chat_id
        if self.token is None or self.chat_id is None:
            logging.warning("TgNotifier: No Telegram credentials found, notification will be disabled")

    def _send(self, text):
        logging.info(text)
        if (
            os.environ.get("ABSCLUST_ENVIRONMENT") == "development"
            or self.token is None
            or self.chat_id is None
        ):
            return
        url = f"https://api.telegram.org/bot{self.token}/sendMessage?chat_id={self.chat_id}&text={text}"
        res = requests.get(url).json()
        if not res["ok"]:
            raise ValueError("Can't send message", res)


def load_env_file():
    with open("../.env", "r") as f:
        for line in f:
            if line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.strip().split("=")
            os.environ[key] = value

load_env_file()

tg_token = os.getenv("TELEGRAM_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")
default_notifier = TgNotifier(token=tg_token, chat_id=chat_id, name="Organization backend")
