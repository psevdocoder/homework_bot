class ServiceError(Exception):
    """Ошибка доступа к эндпоинту."""


class NetworkError(Exception):
    """Ошибка отсутствия сети."""


class EndpointError(Exception):
    """Ошибка, если эндпоинт не корректен."""


class MessageSendError(Exception):
    """Ошибка отправки сообщения."""


class EnvVarsError(Exception):
    """Ошибка пустых переменных окружения."""


class ResponseFormatError(Exception):
    """Ошибка, если формат response не json."""
