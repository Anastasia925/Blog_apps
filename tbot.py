import os
from dotenv import load_dotenv, find_dotenv
from loguru import logger
from telebot import TeleBot
from telebot.types import BotCommand, ReplyKeyboardMarkup, KeyboardButton, Message, ReplyKeyboardRemove
from telebot.custom_filters import StateFilter
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup
from werkzeug.security import generate_password_hash, check_password_hash
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from app import app, db
from app.models import User

logger.add('logs/bot.log', format="{time} {level}    {message}", level="INFO")
logger.add('logs/bot.log', format="{time} {level}    {message}", level="ERROR")
logger.add('logs/bot.log', format="{time} {level}    {message}", level="DEBUG")

if not find_dotenv():
    exit("Environment variables are not loaded because there is no .env file")
else:
    load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DEFAULT_COMMANDS = (
    ('start', "Запустить бота"),
    ('help', "Вывести список команд"),
)


class UserInfoState(StatesGroup):
    """User Status Class"""
    wait_password = State()
    wait_password2 = State()
    wait_username = State()
    wait_pass_connect = State()


storage = StateMemoryStorage()
bot = TeleBot(token=BOT_TOKEN, state_storage=storage)


def set_default_commands(bot) -> None:
    bot.set_my_commands(
        [BotCommand(*i) for i in DEFAULT_COMMANDS]
    )


def menu_buttons() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup()
    keyboard.add((KeyboardButton("/reset")))
    keyboard.add((KeyboardButton("/connect")))
    logger.debug('function -> menu_buttons()')
    return keyboard


# @bot.message_handler(State=None)
# def bot_echo(message: Message):
#     if (message.text).lower() == "привет":
#         bot.send_message(message.from_user.id, f"Привет, {message.from_user.username}")
#         bot.send_message(message.from_user.id, "Выберите команду:", reply_markup=menu_buttons())
#     else:
#         logger.debug(f"/echo -> {message.text}")
#         bot.reply_to(message, "Я тебя не понимаю, напиши 'Привет' или /start")


@bot.message_handler(commands=["help"])
def bot_help(message: Message) -> None:
    """
    The handler of the <help> command.
    Displays a list of commands
    :param message: A message received in the chat
    :return:
    """
    logger.debug("/help")

    text = [f"/{command} - {desk}" for command, desk in DEFAULT_COMMANDS]
    bot.reply_to(message, "\n".join(text))


@bot.message_handler(commands=['start'])
def bot_start(message: Message) -> None:
    """
    The handler of the <start> command.
    Displays a greeting by user name.
    Displays a table of commands.
    :param message: A message received in the chat
    :return:
    """
    logger.debug("/start")
    bot.send_message(message.from_user.id, f'Приветствую {message.from_user.first_name}.\n\n'
                                           'Для подключения к аккаунту выберите команду <connect>.\n\n'
                                           'Для сброса и изменения пароля выберите команду <reset>.\n'
                     , reply_markup=menu_buttons())


@bot.message_handler(commands=["reset"])
def start_script(message: Message) -> None:
    logger.debug("/reset")
    with app.app_context():
        user = db.session.scalar(
            sa.select(User).where(User.telegram == message.from_user.username))
        if user:
            bot.send_message(message.from_user.id,
                             f'Введите ваш новый пароль:',
                             reply_markup=ReplyKeyboardRemove())
            bot.set_state(message.from_user.id, UserInfoState.wait_password, message.chat.id)
            logger.debug("State -> wait_password")
        else:
            bot.send_message(message.from_user.id,
                             f'{message.from_user.first_name}, вы не подключили телеграмм в личном кабинете или не '
                             f'ввели при регистрации',
                             reply_markup=ReplyKeyboardRemove())


@bot.message_handler(state=UserInfoState.wait_password)
def wait_password(message: Message) -> None:
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["password_hash"] = generate_password_hash(message.text)
    bot.send_message(message.from_user.id,
                     f'Повторите пароль:')
    bot.set_state(message.from_user.id, UserInfoState.wait_password2, message.chat.id)
    logger.debug("State -> wait_password2")


@bot.message_handler(state=UserInfoState.wait_password2)
def wait_password2(message: Message) -> None:
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        if check_password_hash(data['password_hash'], message.text):
            with app.app_context():
                user = db.session.scalar(
                    sa.select(User).where(User.telegram == message.from_user.username))
                user.set_password(message.text)
                db.session.add(user)
                db.session.commit()
                bot.send_message(message.from_user.id,
                                 f'Ваш пароль изменен.\n\nВыполните вход используя новый пароль.')
        else:
            bot.send_message(message.from_user.id,
                             f'Пароли не совпадают, повторите выбрав команду <reset>', reply_markup=menu_buttons())
            bot.set_state(message.from_user.id, None, message.chat.id)


@bot.message_handler(commands=["connect"])
def connect(message: Message) -> None:
    logger.debug("/connect")
    bot.send_message(message.from_user.id,
                     f'Введите ваш логин или имя:',
                     reply_markup=ReplyKeyboardRemove())
    bot.set_state(message.from_user.id, UserInfoState.wait_username, message.chat.id)
    logger.debug("State -> wait_username")


@bot.message_handler(state=UserInfoState.wait_username)
def wait_username(message: Message) -> None:
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["username"] = message.text.strip()
    with app.app_context():
        user = db.session.scalar(
            sa.select(User).where(User.username == message.text.strip()))
        if user:
            bot.send_message(message.from_user.id,
                             f'Введите ваш пароль:')
            bot.set_state(message.from_user.id, UserInfoState.wait_pass_connect, message.chat.id)
            logger.debug("State -> wait_pass_connect")
        else:
            bot.send_message(message.from_user.id,
                             f'Пользователь не найден\n\nДля повтора используйте команду <connect>')
            bot.set_state(message.from_user.id, None, message.chat.id)


@bot.message_handler(state=UserInfoState.wait_pass_connect)
def wait_pass_connect(message: Message) -> None:
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        with app.app_context():
            user = db.session.scalar(
                sa.select(User).where(User.username == data['username']))
            if user.check_password(message.text):
                if not user.telegram:
                    try:
                        user.telegram = message.from_user.username
                        db.session.add(user)
                        db.session.commit()
                        bot.send_message(message.from_user.id,
                                         f'Вы подключены\n\nВ профиль добавлена ссылка на этот акаунт.')
                        bot.set_state(message.from_user.id, None, message.chat.id)
                        logger.debug("State -> None")
                    except IntegrityError:
                        bot.send_message(message.from_user.id,
                                         f'Ваш телеграм подключен к другому аккаунту')
                        bot.set_state(message.from_user.id, None, message.chat.id)
                        logger.debug("State -> None")

                elif user.telegram:
                    bot.send_message(message.from_user.id,
                                     f'Вы уже подключены')
                    bot.set_state(message.from_user.id, None, message.chat.id)
                    logger.debug("State -> None")
            else:
                    bot.send_message(message.from_user.id,
                                     f'Не верный пароль, попробуйте еще командой <connect>:', reply_markup=menu_buttons())
                    bot.set_state(message.from_user.id, None, message.chat.id)
                    logger.debug("State -> None")


if __name__ == '__main__':
    with open("logs/bot.log", 'w') as info_log:
        """Clearing bot logs"""
        print('Bot logs cleared')

    bot.add_custom_filter(StateFilter(bot))
    set_default_commands(bot)
    bot.infinity_polling()
