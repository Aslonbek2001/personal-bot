"""aiogram FSM holatini SQLite da saqlaydi (qayta ishga tushganda ham suhbat saqlanadi)."""

from collections.abc import Mapping
from typing import Any

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StateType, StorageKey

from bot.services import db


class SQLiteStorage(BaseStorage):
    @staticmethod
    def _key(key: StorageKey) -> str:
        return f"{key.bot_id}:{key.chat_id}:{key.user_id}"

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        db.fsm_set_state(self._key(key), state.state if isinstance(state, State) else state)

    async def get_state(self, key: StorageKey) -> str | None:
        return db.fsm_get_state(self._key(key))

    async def set_data(self, key: StorageKey, data: Mapping[str, Any]) -> None:
        db.fsm_set_data(self._key(key), dict(data))

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        return db.fsm_get_data(self._key(key))

    async def close(self) -> None:
        pass
