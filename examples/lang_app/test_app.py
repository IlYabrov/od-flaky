"""Четыре теста, разделяющих глобальное состояние STATE (исходный порядок t1..t4)."""
from app import STATE, greet, init_app, query, set_lang


def test_greet():  # t1 - victim: падает, если перед ним язык переключили на ru
    assert greet() == "Hello"


def test_init():  # t2 - cleaner для пары (t4, t1) и state-setter для t3
    init_app()
    assert STATE["lang"] == "en"


def test_query():  # t3 - brittle: проходит, только если раньше был test_init
    assert query() == 42


def test_switch_lang():  # t4 - polluter: оставляет язык ru
    set_lang("ru")
    assert greet() == "Привет"
