import logging
import os
import sys
import time
from dotenv import load_dotenv

import requests
import telegram

from exceptions import InappropriateStatusException, TokenAbsentExeption



logging.basicConfig(
    level=logging.DEBUG,
    filename=f'{__name__}.log',
    format='%(asctime)s, %(levelname)s, %(message)s',
    filemode='w'
)

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)


load_dotenv()

PRACTICUM_TOKEN = os.getenv('PR_TOKEN')
TELEGRAM_TOKEN = os.getenv('TG_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TG_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения"""
    for token in (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID):
        if token is None:
            logging.critical('Отсутствуют обязательные переменные окружения')
            raise TokenAbsentExeption


def send_message(bot, message):
    """Отравляет сообщение в чат"""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение успешно отправлено.')
    except Exception as error:
        logging.error(f'При отправке сообщения произошла ошибка: {error}')


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса"""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        if response.status_code != 200:
            logging.error(
                f'Статус API отличный от ожидаемого.'
                f'{response.status_code}'
            )
            raise InappropriateStatusException('API не отвечает')
        return response.json()
    except requests.exceptions.RequestException as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')


def check_response(response):
    """Проверяет ответ API на соответствие"""
    if not isinstance(response, dict):
        logging.error('Не соответсвует тип данных')
        raise TypeError('Ожидается тип данных словарь')
    if not isinstance(response.get('homeworks'), list):
        logging.error('Не соответсвует тип данных')
        raise TypeError('Ожидается тип данных список')


def parse_status(homework):
    """Извлекает статус конкретной домашней работы"""

    homework_name = homework.get('homework_name')
    status = homework.get('status')

    if homework_name is None or status is None:
        raise ValueError("Отсутствие требуемых ключей в ответе API")

    if status in HOMEWORK_VERDICTS:
        verdict = HOMEWORK_VERDICTS[status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'

    raise ValueError("Недокументированный статус домашней работы")


def main():
    """Основная логика работы бота."""
    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 0  # int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            if response.get('homeworks'):
                current_homework = response.get('homeworks')[0]
                message = parse_status(current_homework)
                send_message(bot, message)
            timestamp = response.get('current_date')
            time.sleep(RETRY_PERIOD)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(f'При отправке сообщения возникла ошибка: {error}.')
            send_message(bot, message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
