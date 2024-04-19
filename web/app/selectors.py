from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from . import models


def get_user(*, user_id: int, db: Session, raise_exception: bool) -> models.User | None:
    """
    Gets User from DB by ID column.

    Returns `None` if not found or raises exception if `raise_exception` argument is `True`.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if raise_exception:
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
            )
    return user
