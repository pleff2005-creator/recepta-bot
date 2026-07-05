"""Хендлеры бота: быстрые кнопки, свободный диалог (Claude/FAQ) и запись (FSM)."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from .ai import ai_reply
from .booking import Booking, save_booking
from .config import OWNER_CHAT_ID
from .knowledge import load_kb

log = logging.getLogger(__name__)
router = Router()

BTN_BOOK = "📅 Записаться"
BTN_SERVICES = "💇 Услуги и цены"
BTN_HOURS = "🕒 Часы работы"
BTN_ADDRESS = "📍 Адрес"

MAIN_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BTN_BOOK)],
        [KeyboardButton(text=BTN_SERVICES), KeyboardButton(text=BTN_HOURS)],
        [KeyboardButton(text=BTN_ADDRESS)],
    ],
    resize_keyboard=True,
    input_field_placeholder="Спросите что угодно или выберите на клавиатуре…",
)

# Короткая история диалога на пользователя — контекст для Claude (в памяти процесса).
_history: dict[int, list[dict]] = {}
_HISTORY_TURNS = 6


class BookingForm(StatesGroup):
    service = State()
    name = State()
    phone = State()
    time = State()


def _remember(uid: int, role: str, text: str) -> None:
    hist = _history.setdefault(uid, [])
    hist.append({"role": role, "content": text})
    del hist[:-_HISTORY_TURNS]


# --------------------------- команды и кнопки ---------------------------

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    _history.pop(message.from_user.id, None)
    await message.answer(load_kb().greeting(), reply_markup=MAIN_KB)


@router.message(Command("cancel"))
@router.message(F.text.casefold() == "отмена")
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    if await state.get_state() is not None:
        await state.clear()
        await message.answer("Запись отменил. Если что — я на связи.", reply_markup=MAIN_KB)
    else:
        await message.answer("Сейчас нечего отменять 🙂", reply_markup=MAIN_KB)


@router.message(F.text == BTN_SERVICES)
async def show_services(message: Message) -> None:
    await message.answer(load_kb().services_text(), reply_markup=MAIN_KB)


@router.message(F.text == BTN_HOURS)
async def show_hours(message: Message) -> None:
    await message.answer(load_kb().hours_text(), reply_markup=MAIN_KB)


@router.message(F.text == BTN_ADDRESS)
async def show_address(message: Message) -> None:
    await message.answer(load_kb().address_text(), reply_markup=MAIN_KB)


# ------------------------------- запись (FSM) -------------------------------

@router.message(F.text == BTN_BOOK)
async def book_start(message: Message, state: FSMContext) -> None:
    await state.set_state(BookingForm.service)
    services = ", ".join(load_kb().service_names())
    await message.answer(
        f"Отлично! На какую услугу записать?\nНапример: {services}.\n\n(«отмена» — выйти)"
    )


@router.message(BookingForm.service, F.text)
async def book_service(message: Message, state: FSMContext) -> None:
    await state.update_data(service=message.text.strip())
    await state.set_state(BookingForm.name)
    await message.answer("Как вас зовут?")


@router.message(BookingForm.name, F.text)
async def book_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text.strip())
    await state.set_state(BookingForm.phone)
    await message.answer("Оставьте телефон для подтверждения 📱")


@router.message(BookingForm.phone, F.text)
async def book_phone(message: Message, state: FSMContext) -> None:
    await state.update_data(phone=message.text.strip())
    await state.set_state(BookingForm.time)
    await message.answer("На какой день и время вам удобно? Например: «завтра после 18:00».")


@router.message(BookingForm.time, F.text)
async def book_time(message: Message, state: FSMContext) -> None:
    data = await state.update_data(time=message.text.strip())
    await state.clear()

    user = message.from_user
    booking = Booking(
        service=data["service"],
        name=data["name"],
        phone=data["phone"],
        wanted_time=data["time"],
        tg_user=f"@{user.username}" if user.username else str(user.id),
    )
    booking_id = save_booking(booking)

    await message.answer(
        "Готово! ✅ Заявка принята:\n"
        f"• Услуга: {booking.service}\n"
        f"• Имя: {booking.name}\n"
        f"• Телефон: {booking.phone}\n"
        f"• Желаемое время: {booking.wanted_time}\n\n"
        "Администратор подтвердит запись и напишет вам. Спасибо! 🌿",
        reply_markup=MAIN_KB,
    )

    await _notify_owner(message, booking, booking_id)


async def _notify_owner(message: Message, booking: Booking, booking_id: int) -> None:
    text = (
        f"🔔 Новая заявка #{booking_id}\n"
        f"Услуга: {booking.service}\n"
        f"Имя: {booking.name}\n"
        f"Телефон: {booking.phone}\n"
        f"Время: {booking.wanted_time}\n"
        f"Клиент: {booking.tg_user}"
    )
    if OWNER_CHAT_ID:
        try:
            await message.bot.send_message(int(OWNER_CHAT_ID), text)
            return
        except Exception as e:  # неверный chat_id и т.п. — не роняем клиентский поток
            log.warning("Не удалось уведомить владельца: %s", e)
    log.info("НОВАЯ ЗАЯВКА (owner chat не настроен):\n%s", text)


# --------------------------- свободный диалог ---------------------------

@router.message(StateFilter(None), F.text)
async def free_chat(message: Message) -> None:
    uid = message.from_user.id
    text = message.text.strip()
    _remember(uid, "user", text)

    # 1) живой ответ Claude (если задан ключ) — строго по базе знаний
    reply = await ai_reply(text, history=_history.get(uid, [])[:-1])

    # 2) откат на встроенный FAQ-движок (работает без ключа и без сети)
    if not reply:
        reply = load_kb().answer(text)

    # 3) не поняли — мягкая заглушка + путь к записи
    if not reply:
        reply = (
            "Не уверен, что понял вопрос 🙂 Могу рассказать про услуги и цены, часы "
            "работы, адрес — или сразу записать вас. Что удобнее?"
        )

    _remember(uid, "assistant", reply)
    await message.answer(reply, reply_markup=MAIN_KB)
