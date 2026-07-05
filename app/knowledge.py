"""База знаний салона + встроенный (keyless) движок ответов.

Работает без интернета и без API-ключа: сопоставляет вопрос клиента с FAQ и
услугами по ключевым словам и нечёткому совпадению. Это «страховка» — даже если
Claude недоступен или ключ не задан, бот всё равно отвечает по делу.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache

from .config import KB_PATH


@dataclass
class KnowledgeBase:
    raw: dict

    # --- удобные срезы ---
    @property
    def biz(self) -> dict:
        return self.raw["business"]

    @property
    def services(self) -> list[dict]:
        return self.raw["services"]

    @property
    def faq(self) -> list[dict]:
        return self.raw["faq"]

    @property
    def persona(self) -> dict:
        return self.raw.get("persona", {})

    # --- форматирование готовых блоков ---
    def greeting(self) -> str:
        return self.persona.get("greeting", f"Здравствуйте! Это администратор «{self.biz['name']}».")

    def services_text(self) -> str:
        lines = [f"💇 Услуги и цены — {self.biz['name']}:", ""]
        for s in self.services:
            lines.append(f"• {s['name']} — от {s['price_from']} ₽ ({s['duration']})")
        lines.append("")
        lines.append("Цены «от» — итог зависит от длины волос и мастера. Хотите записаться?")
        return "\n".join(lines)

    def hours_text(self) -> str:
        h = self.biz["hours"]
        lines = ["🕒 График работы:"]
        for day, val in h.items():
            lines.append(f"• {day}: {val}")
        return "\n".join(lines)

    def address_text(self) -> str:
        b = self.biz
        parts = [f"📍 {b['name']} — {b['address']}."]
        if b.get("landmark"):
            parts.append(b["landmark"].capitalize() + ".")
        if b.get("parking"):
            parts.append(b["parking"].capitalize() + ".")
        return " ".join(parts)

    def service_names(self) -> list[str]:
        return [s["name"] for s in self.services]

    # --- keyless-движок: попытка ответить по FAQ / услугам ---
    def answer(self, text: str) -> str | None:
        norm = _normalize(text)
        if not norm:
            return None

        # 1) прямое совпадение по ключевым словам FAQ
        for item in self.faq:
            for kw in item.get("keywords", []):
                if kw in norm:
                    return item["a"]

        # 2) вопрос про конкретную услугу / её цену
        service = self._match_service(norm)
        if service:
            return (
                f"{service['name']} — от {service['price_from']} ₽, "
                f"{service['duration']}. Записать вас?"
            )

        # 3) нечёткое совпадение с вопросами FAQ (опечатки, перефразировки)
        best, score = None, 0.0
        for item in self.faq:
            s = _similarity(norm, _normalize(item["q"]))
            if s > score:
                best, score = item, s
        if best and score >= 0.62:
            return best["a"]

        return None

    def _match_service(self, norm: str) -> dict | None:
        for s in self.services:
            terms = [s["name"], *s.get("aliases", [])]
            for term in terms:
                if _normalize(term) in norm:
                    return s
        return None


def _normalize(text: str) -> str:
    text = text.lower().replace("ё", "е")
    return re.sub(r"[^a-zа-я0-9 ]+", " ", text).strip()


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


@lru_cache(maxsize=1)
def load_kb() -> KnowledgeBase:
    with open(KB_PATH, encoding="utf-8") as f:
        return KnowledgeBase(json.load(f))
