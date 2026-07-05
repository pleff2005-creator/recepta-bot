"""Конфигурация из окружения. Ничего секретного в коде — всё через .env."""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv опционален — переменные можно задать и вручную
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
KB_PATH = Path(os.getenv("KB_PATH", BASE_DIR / "data" / "salon.json"))

# Токен Telegram-бота от @BotFather — обязателен для запуска.
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Ключ Anthropic — ОПЦИОНАЛЕН. Без него бот работает на встроенном FAQ-движке
# (демо не падает, ответы бесплатны). С ключом — Claude отвечает живым языком.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()

# Дешёвая и быстрая модель под высокий поток сообщений ресепшена.
# Можно поднять до "claude-opus-4-8" для максимального качества.
MODEL_ID = os.getenv("MODEL_ID", "claude-haiku-4-5").strip()

# Chat ID владельца/администратора — куда падают уведомления о новых записях.
# Узнать свой ID можно у @userinfobot. Пусто → уведомления в лог.
OWNER_CHAT_ID = os.getenv("OWNER_CHAT_ID", "").strip()

AI_ENABLED = bool(ANTHROPIC_API_KEY)
