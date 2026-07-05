"""Оффлайн-демо встроенного FAQ-движка — без токена и без интернета.

Запуск: python demo.py
Показывает, как бот отвечает на типичные вопросы клиентов на одной базе знаний.
"""
import sys

# На Windows консоль по умолчанию не UTF-8 — иначе эмодзи ломают вывод.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.knowledge import load_kb

QUESTIONS = [
    "сколько стоит женская стрижка?",
    "вы делаете балаяж?",
    "где вы находитесь",
    "во сколько открываетесь в воскресенье?",
    "можно оплатить картой?",
    "хочу записаться",
    "есть ли парковка",
    "скок стоит маникюр",  # опечатка → нечёткое совпадение
]


def main() -> None:
    kb = load_kb()
    print(kb.greeting())
    print("=" * 60)
    for q in QUESTIONS:
        a = kb.answer(q) or "(→ передаётся Claude / уточняем у мастера)"
        print(f"👤 {q}\n🤖 {a}\n")


if __name__ == "__main__":
    main()
