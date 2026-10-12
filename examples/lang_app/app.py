"""Мини-приложение с глобальным состоянием - авторский иллюстративный пример."""
STATE = {"lang": "en", "db": None}


def greet():
    return "Привет" if STATE["lang"] == "ru" else "Hello"


def set_lang(lang):
    STATE["lang"] = lang


def init_app():
    """Сбрасывает язык и «подключает» базу данных."""
    STATE.update(lang="en", db={"answer": 42})


def query():
    return STATE["db"]["answer"]  # TypeError, если база не подключена
