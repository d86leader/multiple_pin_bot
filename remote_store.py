#!/ust/bin/env python3

from typing import *
from redis import Redis
from message_info import MessageInfo
import json

"""
Author: d86leader@mail.com, 2019
License: published under GNU GPL-3

Description: proxy types to the means of storage.
This presents the same interface as local_store, but uses the remote redis
server for storing data
"""

class Storage:
    RedisAddr = "redis"
    RedisPort = 6379

    def __init__(self, addr=RedisAddr, port=RedisPort) -> None:
        # manual said it's thread-safe to do this
        self._pins_db = Redis(host=addr, port=port, db=0)
        self._editables_db = Redis(host=addr, port=port, db=1)
        self._no_user_wrote = Redis(host=addr, port=port, db=2)


    def has(self, chat_id: int) -> bool:
        redis = self._pins_db
        key = str(chat_id)
        return redis.llen(key) != 0

    def get(self, chat_id: int) -> List[MessageInfo]:
        redis = self._pins_db
        key = str(chat_id)
        dumps = redis.lrange(key, 0, -1)
        return list(map(MessageInfo.loads, dumps))

    def add(self, chat_id: int, msg: MessageInfo) -> None:
        redis = self._pins_db
        key = str(chat_id)
        value = msg.dumps()
        redis.lpush(key, value)

    def clear(self, chat_id: int) -> None:
        redis = self._pins_db
        key = str(chat_id)
        redis.delete(key)

    def clear_keep_last(self, chat_id: int) -> None:
        redis = self._pins_db
        key = str(chat_id)
        redis.ltrim(key, 0, 0)

    def remove(self, chat_id: int, m_id: int, hint: int = 0) -> None:
        redis = self._pins_db
        key = str(chat_id)
        dumps = redis.lrange(key, 0, -1)

        # calculate indicies to drop
        all_bad = [(abs(index - hint), index)
                      for index, dump in enumerate(dumps)
                      if json.loads(dump)['m_id'] == m_id
                  ]
        if all_bad == []:
            return

        to_delete = min(all_bad)[1]
        # set the indicies to special value
        special = "$$DELETED"
        redis.lset(key, to_delete, special)
        # delete the special value
        redis.lrem(key, 0, special)

    def replace_same_id(self, chat_id: int, edited: MessageInfo) -> None:
        redis = self._pins_db
        key = str(chat_id)
        dumps = redis.lrange(key, 0, -1)
        value = edited.dumps()

        for dump, index in zip(dumps, range(len(dumps))):
            if json.loads(dump)['m_id'] == edited.m_id:
                redis.lset(key, index, value)


    # get and set id of message that you need to edit
    def get_message_id(self, chat_id: int) -> int:
        redis = self._editables_db
        key = str(chat_id)
        return int(redis.get(key))
    def set_message_id(self, chat_id: int, m_id: int) -> None:
        redis = self._editables_db
        key = str(chat_id)
        val = str(m_id)
        redis.set(key, val)
        # automatically set that no user has messaged us
        self._no_user_wrote.set(key, ".")
    def has_message_id(self, chat_id: int) -> bool:
        redis = self._editables_db
        key = str(chat_id)
        return redis.get(key) is not None
    def remove_message_id(self, chat_id: int) -> None:
        redis = self._editables_db
        key = str(chat_id)
        redis.delete(key)

    # status of last message
    def did_user_message(self, chat_id: int) -> bool:
        redis = self._no_user_wrote
        key = str(chat_id)
        return redis.get(key) is None
    def user_message_added(self, chat_id: int) -> None:
        redis = self._no_user_wrote
        key = str(chat_id)
        redis.delete(key)
