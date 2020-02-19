#!/usr/bin/env python
# Source: http://code.activestate.com/recipes/325905-memoize-decorator-with-timeout/#c1

import logging
import time
import traceback

import ruamel.yaml
from telegram import ChatPermissions
from telegram.ext.dispatcher import run_async

FullChatPermissions = ChatPermissions(
    can_send_messages=True,
    can_send_media_messages=True,
    can_send_polls=True,
    can_send_other_messages=True,
    can_add_web_page_previews=True,
    can_change_info=True,
    can_invite_users=True,
    can_pin_messages=True,
)

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger("Telegram_Group_Easyauth")

yaml = ruamel.yaml.YAML()


class MWT(object):
    """Memoize With Timeout"""

    _caches = {}
    _timeouts = {}

    def __init__(self, timeout=2):
        self.timeout = timeout

    def collect(self):
        """Clear cache of results which have timed out"""
        for func in self._caches:
            cache = {}
            for key in self._caches[func]:
                if (time.time() - self._caches[func][key][1]) < self._timeouts[func]:
                    cache[key] = self._caches[func][key]
            self._caches[func] = cache

    def __call__(self, f):
        self.cache = self._caches[f] = {}
        self._timeouts[f] = self.timeout

        def func(*args, **kwargs):
            kw = sorted(kwargs.items())
            key = (args, tuple(kw))
            try:
                v = self.cache[key]
                if (time.time() - v[1]) > self.timeout:
                    raise KeyError
            except KeyError:
                v = self.cache[key] = f(*args, **kwargs), time.time()
            return v[0]

        func.func_name = f.__name__

        return func


@MWT(timeout=60 * 60)
def get_chat_admins(bot, chat_id, extra_user):
    if extra_user is not None and isinstance(extra_user, int):
        users = [extra_user]
    else:
        users = extra_user
    admins = [admin.user.id for admin in bot.get_chat_administrators(chat_id)]
    if users:
        admins.extend(users)
    return admins


def collect_error(func):
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            logger.info(traceback.format_exc())

    return wrapped
