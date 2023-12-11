class TokenAbsentExeption(Exception):
    """Отсутсвие обязательного токена."""

    pass


class InappropriateStatusException(Exception):
    """Несоответствие статуса ответа API."""

    pass
