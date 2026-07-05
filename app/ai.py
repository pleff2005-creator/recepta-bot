"""Опциональный слой Claude: живые ответы, но строго по базе знаний салона.

Если ANTHROPIC_API_KEY не задан или запрос падает — возвращаем None, и вызывающий
код откатывается на встроенный FAQ-движок. Демо не должно ломаться никогда.
"""
from __future__ import annotations

import logging

from .config import AI_ENABLED, ANTHROPIC_API_KEY, MODEL_ID
from .knowledge import KnowledgeBase, load_kb

log = logging.getLogger(__name__)

_client = None  # ленивая инициализация AsyncAnthropic


def _get_client():
    global _client
    if _client is None:
        from anthropic import AsyncAnthropic

        _client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY, timeout=20.0)
    return _client


def build_system_prompt(kb: KnowledgeBase) -> str:
    b = kb.biz
    services = "\n".join(
        f"- {s['name']}: от {s['price_from']} ₽, {s['duration']}" for s in kb.services
    )
    hours = "\n".join(f"- {d}: {v}" for d, v in b["hours"].items())
    faq = "\n".join(f"- В: {i['q']}\n  О: {i['a']}" for i in kb.faq)
    persona = kb.persona

    return f"""Ты — администратор {b['kind']} «{b['name']}» в городе {b['city']}.
Твоя задача: отвечать клиентам в мессенджере как живой, вежливый администратор —
{persona.get('tone', 'тепло и по делу')}.

СТРОГИЕ ПРАВИЛА:
- Отвечай ТОЛЬКО на основе информации ниже. Если данных нет — честно скажи, что
  уточнишь у мастера, и предложи оставить контакт. Ничего не выдумывай (цены,
  адреса, акции).
- Пиши коротко: 1–3 предложения. Без канцелярита и без «Здравствуйте» в каждом
  сообщении (только в первом).
- {persona.get('handoff', 'Если клиент хочет записаться — предложи оформить запись.')}
- Пиши по-русски.

ДАННЫЕ САЛОНА
Адрес: {b['address']} ({b.get('landmark', '')})
Парковка: {b.get('parking', 'нет данных')}
Оплата: {b.get('payment', 'нет данных')}
Телефон: {b['phone']}
Сайт: {b.get('site', '')}

График работы:
{hours}

Услуги и цены (цены указаны «от»):
{services}

Частые вопросы:
{faq}
"""


async def ai_reply(user_text: str, history: list[dict] | None = None) -> str | None:
    """Ответ Claude по базе знаний. None → откат на keyless-движок."""
    if not AI_ENABLED:
        return None

    kb = load_kb()
    messages = list(history or [])
    messages.append({"role": "user", "content": user_text})

    try:
        client = _get_client()
        resp = await client.messages.create(
            model=MODEL_ID,
            max_tokens=400,
            system=[
                {
                    "type": "text",
                    "text": build_system_prompt(kb),
                    # Стабильный префикс — кэшируем ради дешёвого высокого потока.
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=messages,
        )
        if resp.stop_reason == "refusal":
            return None
        for block in resp.content:
            if block.type == "text" and block.text.strip():
                return block.text.strip()
        return None
    except Exception as e:  # сеть, лимиты, кривой ключ — тихо откатываемся
        log.warning("Claude недоступен, откат на FAQ-движок: %s", e)
        return None
