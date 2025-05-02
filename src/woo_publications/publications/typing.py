from datetime import datetime
from typing import TypedDict
from uuid import UUID

from .constants import DocumentActionTypeOptions


class DocumentAction(TypedDict):
    soort_handeling: DocumentActionTypeOptions
    identifier: str
    at_time: datetime
    was_assciated_with: UUID | None


type DocumentActions = list[DocumentAction]
