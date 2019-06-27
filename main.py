#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import os
import random
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (CallbackQueryHandler, CommandHandler, Filters,
                          MessageHandler, Updater)
from telegram.ext.dispatcher import run_async
from telegram.error import BadRequest
from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

try:
    config = load(
        open(os.path.split(os.path.realpath(__file__))[0] + '/config.yml'), Loader=Loader)
except FileNotFoundError:
    logger.exception("Cannot find config.yml.")
    exit(1)

queue = {}


@run_async
def start(update, context):
    update.message.reply_text(config['START'])


@run_async
def error(update, context):
    logger.warning('Update "%s" caused error "%s"', context, error)


@run_async
def kick(context):
    data = context.job.context.split('|')
    try:
        context.bot.kick_chat_member(chat_id=data[0], user_id=data[1],
                                     until_date=datetime.timestamp(datetime.today()) + config['BANTIME'])
    except BadRequest:
        logger.warning(
            f"Not enough rights to kick chat member {data[1]} at group {data[0]}")


@run_async
def clean(context):
    data = context.job.context.split('|')
    try:
        context.bot.delete_message(chat_id=data[0], message_id=data[1])
        context.bot.delete_message(chat_id=data[0], message_id=data[2])
    except BadRequest:
        logger.warning(
            f"Not enough rights to delete message for chat member {data[1]} or {data[2]} at group {data[0]}")


@run_async
def newmem(update, context):
    message_id = update.message.message_id
    chat = update.message.chat
    from_user = update.message.from_user
    new_chat_members = update.message.new_chat_members
    flag = random.randint(0, len(config['CHALLENGE']) - 1)
    if from_user.id not in [admin.user.id for admin in context.bot.get_chat_administrators(chat.id)]:
        for user in new_chat_members:
            if not user.is_bot:
                buttons = [[InlineKeyboardButton(
                    text=config['CHALLENGE'][flag]['ANSWER'], callback_data=f"newmem|pass|{user.id}|{flag}")]]
                for t in config['CHALLENGE'][flag]['WRONG']:
                    buttons.append([InlineKeyboardButton(
                        text=t, callback_data=f"newmem|fail|{user.id}|{flag}|{t}")])
                random.shuffle(buttons)
                msg = update.message.reply_text(config['GREET'] % (config['CHALLENGE'][flag]['QUESTION'], config['TIME']),
                                                reply_markup=InlineKeyboardMarkup(buttons))
                try:
                    context.bot.restrict_chat_member(
                        chat_id=chat.id,
                        user_id=user.id,
                        can_send_messages=False,
                        can_send_media_messages=False,
                        can_send_other_messages=False,
                        can_add_web_page_previews=False
                    )
                except BadRequest:
                    logger.warning(
                        f"Not enough rights to restrict chat member {chat.id} at group {user.id}")
                queue[str(chat.id) + str(user.id) + 'kick'] = updater.job_queue.run_once(
                    kick, config['TIME'], context=f"{chat.id}|{user.id}")
                queue[str(chat.id) + str(user.id) + 'clean'] = updater.job_queue.run_once(
                    clean, config['TIME'], context=f"{chat.id}|{msg.message_id}|{message_id}")


@run_async
def query(update, context):
    user = update.callback_query.from_user
    message = update.callback_query.message
    chat = message.chat
    data = update.callback_query.data.split('|')
    if str(user.id) == data[2]:
        if data[1] == 'pass':
            context.bot.answer_callback_query(
                text=config['SUCCESS'],
                show_alert=False,
                callback_query_id=update.callback_query.id
            )
            context.bot.edit_message_text(
                text=f"[{user.first_name}](tg://user?id={user.id}) {config['PASS']}",
                message_id=message.message_id,
                chat_id=chat.id, parse_mode='Markdown'
            )
            try:
                context.bot.restrict_chat_member(
                    chat_id=chat.id,
                    user_id=user.id,
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True
                )
            except BadRequest:
                logger.warning(
                    f"Not enough rights to restrict chat member {chat.id} at group {user.id}")
        else:
            context.bot.answer_callback_query(
                text=config['RETRY'] % config['BANTIME'],
                show_alert=True,
                callback_query_id=update.callback_query.id
            )
            try:
                context.bot.kick_chat_member(chat_id=chat.id, user_id=user.id,
                                             until_date=datetime.timestamp(datetime.today()) + config['BANTIME'])
            except BadRequest:
                context.bot.edit_message_text(
                    text=f"[{user.first_name}](tg://user?id={user.id}) {config['NOT_KICK']}\n{config['CHALLENGE'][int(data[3])]['QUESTION']}:{data[4]}",
                    message_id=message.message_id,
                    chat_id=chat.id, parse_mode='Markdown')
                logger.warning(
                    f"Not enough rights to kick chat member {chat.id} at group {user.id}")
            else:
                context.bot.edit_message_text(
                    text=f"[{user.first_name}](tg://user?id={user.id}) {config['KICK']}\n{config['CHALLENGE'][int(data[3])]['QUESTION']}:{data[4]}",
                    message_id=message.message_id,
                    chat_id=chat.id, parse_mode='Markdown')
        queue[str(chat.id) + str(user.id) + 'kick'].schedule_removal()
    else:
        context.bot.answer_callback_query(
            text=config['OTHER'], show_alert=True, callback_query_id=update.callback_query.id)


if __name__ == '__main__':
    updater = Updater(config['TOKEN'], use_context=True)
    updater.dispatcher.add_handler(CommandHandler("start", start))
    updater.dispatcher.add_handler(MessageHandler(
        Filters.status_update.new_chat_members, newmem))
    updater.dispatcher.add_handler(
        CallbackQueryHandler(query, pattern=r'newmem'))
    updater.dispatcher.add_error_handler(error)
    updater.start_polling()
    updater.idle()
