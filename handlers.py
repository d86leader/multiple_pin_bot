#!/usr/bin/env/python3

from typing import *
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from storage import Storage, MessageInfo
from enum import Enum


# decorator: curry first positional argument of function
def curry(func):
    def curried1(arg):
        def rest(*args, **kwargs):
            return func(arg, *args, **kwargs)
        return rest
    return curried1


def start(bot, update):
    update.message.reply_text("Start")

def help(bot, update):
    update.message.reply_text("Don't panic!")

@curry
def error(logger, bot, update, whatisthisparam):
    logger.warning(f"Update '{update}' caused error: {context.error}")


@curry
def pinned(storage : Storage, bot, update):
    if update.message.from_user.is_bot:
        return

    chat_id = update.message.chat_id
    msg_info = MessageInfo(update.message.pinned_message)

    storage.add(chat_id, msg_info)

    text, layout = gen_post(storage, chat_id)
    sent_msg = bot.send_message(chat_id, text=text, reply_markup=layout)
    sent_id = sent_msg.message_id

    # remember the message for future edits
    storage.set_message_id(chat_id, sent_id)
    bot.pin_chat_message(chat_id, sent_id, disable_notification=True)

@curry
def button_pressed(storage : Storage, bot, update):
    cb = update.callback_query
    chat_id = cb.message.chat_id

    if cb.data == CallbackData.UnpinAll:
        storage.clear(chat_id)
        cb.answer("")
    elif cb.data == CallbackData.KeepLast:
        storage.clear_keep_last(chat_id)
        cb.answer("")
    else:
        msg_id = int(cb.data)
        storage.remove(chat_id, msg_id)
        cb.answer("")

    text, layout = gen_post(storage, chat_id)
    msg_id = storage.get_message_id(chat_id)

    bot.edit_message_text(
        chat_id       = chat_id# + (1 << 64) if chat_id < 0 else chat_id
        ,message_id   = msg_id
        ,text         = text
        ,reply_markup = layout
        )


class CallbackData(Enum):
    UnpinAll = "$$ALL"
    KeepLast = "$$LAST"

# used in two handlers above
def gen_post(storage : Storage, chat_id : int) -> Tuple[str, InlineKeyboardMarkup]:
    pins = storage.get(chat_id)
    text = "\n\n".join(map(str, pins))
    text += "\n\nUnpin:"

    # generate buttons for pin control
    button_all = InlineKeyboardButton("Unpin all"
                                     ,callback_data=str(CallbackData.UnpinAll))
    button_keep_last = InlineKeyboardButton("Keep last"
                                     ,callback_data=str(CallbackData.KeepLast))
    # first two rows: those buttons
    layout = [[button_all], [button_keep_last]]

    # other buttons: this style with message_id as data
    def on_button(msg, index) -> str:
        return f"{index} {msg.icon}"
        #return f"{index} {msg.icon} {msg.sender}"

    texts = (on_button(msg, index + 1) for msg,index in zip(pins, range(len(pins))))
    cb_datas = (msg.m_id for msg in pins)

    buttons = [InlineKeyboardButton(text, callback_data=str(data))
                for text, data in zip(texts, cb_datas)]
    # split buttons by lines
    on_one_line = 3
    rows = [buttons[i:i+on_one_line] for i in range(0, len(buttons), on_one_line)]

    layout += rows

    return (text, InlineKeyboardMarkup(layout))