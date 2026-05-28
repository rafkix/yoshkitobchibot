from typing import List, Union

from aiogram.filters import BaseFilter
from aiogram.types import Message


class IsAdmin(BaseFilter):
    def __init__(self, admin_ids: Union[int, List[int]]) -> None:
        self.admin_ids = admin_ids

    async def __call__(self, message: Message) -> bool:
        """
        Check if the user is an admin.
        :param message: The message object to check.
        :return: True if the user is an admin, False otherwise.
        """
        if isinstance(self.admin_ids, int):
            return message.from_user.id == self.admin_ids
        return message.from_user.id in self.admin_ids
