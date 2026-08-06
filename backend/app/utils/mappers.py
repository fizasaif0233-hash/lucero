from uuid import UUID

from app.core.security import CurrentUser
from app.models.schemas import UserOut, UserRole


def to_user_out(user: CurrentUser) -> UserOut:
    return UserOut(
        id=UUID(user.id),
        email=user.email,
        full_name=user.full_name,
        role=UserRole(user.role),
    )
