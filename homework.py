import logging
import os
import sys
import time
from http import HTTPStatus
from pathlib import Path

import requests
import telegram
from dotenv import load_dotenv

from const_messages import ENV_VAR_IS_EMPTY, ENV_VAR_IS_MISSING, \
    SEND_MESSAGE_FAILURE, CONNECTION_ERROR, WRONG_ENDPOINT
from exceptions import MessageSendError, NetworkError, EndpointError, \
    ResponseFormatError, ServiceError

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    env_var = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, ENDPOINT]
    if not all(env_var):
        logging.critical(ENV_VAR_IS_EMPTY)
        return False
    if None in env_var:
        logging.critical(ENV_VAR_IS_MISSING)
        return False
    return True


def send_message(bot, message):
    """Отправляет сообщение пользователю в Телеграм."""
    try:
        logging.info(f'Trying to send message{message}')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as error:
        logging.error(SEND_MESSAGE_FAILURE.format(
            error=error,
            message=message,
        ))
        raise MessageSendError(error)
    logging.debug(f'Message "{message}" is sent')


def get_api_answer(current_timestamp):
    """Делает запрос к API-сервиса. В случае успеха, возвращает json ответ."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    request_params = dict(url=ENDPOINT, headers=HEADERS, params=params)
    try:
        response = requests.get(**request_params)
    except Exception as error:
        raise NetworkError(CONNECTION_ERROR.format(
            error=error,
            url=ENDPOINT,
            headers=HEADERS,
            params=params
        ))
    response_status = response.status_code
    if response_status != HTTPStatus.OK:
        raise EndpointError(WRONG_ENDPOINT.format(
            response_status=response_status,
            url=ENDPOINT,
            headers=HEADERS,
            params=params
        ))
    try:
        return response.json()
    except Exception as error:
        raise ResponseFormatError(f'Not a json format: {error}')


def check_response(response):
    """
    Возвращает домашку, если есть.
    Проверяет валидность её статуса.
    """
    if not isinstance(response, dict):
        raise TypeError('Response doesn`t conform response type')
    if 'homeworks' not in response:
        raise KeyError('Missing `homeworks` key in response')
    if not isinstance(response['homeworks'], list):
        raise TypeError('Homework data doesn`t conform list type')
    if 'code' in response:
        raise ServiceError(response.get('code'))
    return response['homeworks']


def parse_status(homework):
    """Возвращает текст сообщения от ревьюера."""
    homework_name = homework.get('homework_name')
    if 'homework_name' not in homework:
        raise KeyError(f'Отсутствует ключ: {homework_name}')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise NameError(homework_status)
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Ошибка переменной окружения')
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if not homework:
                message = 'Статус работы не изменился'
                logging.info(message)
            else:
                message = parse_status(homework[0])
                send_message(bot, message)
                logging.info(homework)
                current_timestamp = response.get('current_date')
        except IndexError:
            message = 'Статус работы не изменился'
            logging.info(message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s, %(message)s, %(lineno)d, %(name)s',
        filemode='w',
        filename=f'{Path(__file__).stem}.log',
        level=logging.DEBUG,
    )
    main()
