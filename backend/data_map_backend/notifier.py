import logging
import os

import requests

WORDS_IN_USERNAMES_TO_EXCLUDE_FOR_NOTIFICATIONS = os.environ.get(
    "WORDS_IN_USERNAMES_TO_EXCLUDE_FOR_NOTIFICATIONS", ""
).split(",")


class BaseNotifier:
    def __init__(self, name) -> None:
        self.name = name

    def _send(self, text):
        raise NotImplementedError()

    def send(self, kind, message, user=None):
        if user and user.is_staff:
            # not logging staff actions for now
            return
        for word in WORDS_IN_USERNAMES_TO_EXCLUDE_FOR_NOTIFICATIONS:
            if user and word in user.email:
                # not logging user actions for now
                return
        prfx = kind + ": \n"
        if self.name:
            prfx += self.name + ", "
        try:
            self._send(prfx + message)
        except Exception as e:
            logging.warn(f"Can't send notification, {repr(e)}")

    def info(self, message, user=None):
        self.send("Info", message, user)

    def warning(self, message, user=None):
        self.send("Warning", message, user)

    def error(self, message, user=None):
        self.send("Error", message, user)


class TgNotifier(BaseNotifier):
    def __init__(self, token=None, chat_id=None, name="") -> None:
        super().__init__(name)
        self.token = token
        self.chat_id = chat_id
        if self.token is None or self.chat_id is None:
            logging.warning("TgNotifier: No Telegram credentials found, notification will be disabled")

    def _send(self, text):
        logging.info(text)
        if os.environ.get("ABSCLUST_ENVIRONMENT") == "development" or self.token is None or self.chat_id is None:
            return
        url = f"https://api.telegram.org/bot{self.token}/sendMessage?chat_id={self.chat_id}&text={text}"
        res = requests.get(url).json()
        if not res["ok"]:
            raise ValueError("Can't send message", res)


tg_token = os.getenv("TELEGRAM_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")
default_notifier = TgNotifier(token=tg_token, chat_id=chat_id, name="Organization backend")
