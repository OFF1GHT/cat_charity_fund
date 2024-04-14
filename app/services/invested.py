from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CharityProject, Donation
from app.crud.base import CRUDBase
from app.core.constants import MIN_AMOUNT


async def investing_process(entity, session: AsyncSession):
    if entity.invested_amount >= entity.full_amount:
        return

    free_amount = entity.full_amount - entity.invested_amount
    crud = Donation if isinstance(entity, CharityProject) else CharityProject
    unclosed_objects = await CRUDBase(crud).get_unclosed_objects(session)

    for db_object in unclosed_objects:
        amount_to_invest = min(
            free_amount, db_object.full_amount - db_object.invested_amount
        )
        db_object.invested_amount += amount_to_invest
        entity.invested_amount += amount_to_invest
        free_amount -= amount_to_invest

        if db_object.invested_amount == db_object.full_amount:
            db_object.fully_invested = True
            db_object.close_date = datetime.now()

        if free_amount == MIN_AMOUNT:
            break

    if entity.invested_amount == entity.full_amount:
        entity.fully_invested = True
        entity.close_date = datetime.now()

    session.add(entity)
    await session.commit()
    await session.refresh(entity)