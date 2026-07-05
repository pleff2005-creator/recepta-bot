"""Сборка и запуск бота (aiogram 3, long polling)."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher

from .config import AI_ENABLED, BOT_TOKEN, MODEL_ID
from .handlers import router


async def run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    log = logging.getLogger("recepta")

    if not BOT_TOKEN:
        raise SystemExit(
            "BOT_TOKEN не задан. Получите токен у @BotFather и положите в .env "
            "(BOT_TOKEN=...). См. README."
        )

    if AI_ENABLED:
        log.info("Режим: Claude (%s) + FAQ-страховка", MODEL_ID)
    else:
        log.info("Режим: встроенный FAQ-движок (ANTHROPIC_API_KEY не задан — бесплатно)")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


def main() -> None:
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()
