from fastapi import HTTPException
from typing import Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.crud.donation import donation_crud
from app.crud.charity_project import charity_project_crud
from app.models import CharityProject, Donation
from app.schemas.charity_project import (
    CharityProjectUpdate,
    CharityProjectCreate,
)
from app.core.constants import MIN_AMOUNT
from app.models import User


class CharityProjectService:
    def __init__(self, session):
        self.session = session

    async def check_charity_project_sum(self, charity_project: CharityProject.id) -> None:
        """Проверка на присутствие/отсутствие инвестиций в проекте."""
        if charity_project.invested_amount > MIN_AMOUNT:
            raise HTTPException(
                status_code=400,
                detail='Проверка на присутствие/отсутствие инвестиций в проекте',
            )

    async def charity_project_remove(self, charity_project_id: int):
        charity_project = await self.get_charity_project(charity_project_id)
        await self.check_charity_project_sum(charity_project)
        return charity_project

    async def check_name_duplicate(self, charity_project_name: str) -> None:
        charity_project_id = await charity_project_crud.get_project_id_by_name(
            charity_project_name, self.session
        )
        if charity_project_id is not None:
            raise HTTPException(
                status_code=400, detail='Проект с таким именем уже существует!'
            )

    async def get_charity_project(self, charity_project_id: int) -> CharityProject:
        charity_project = await charity_project_crud.get(
            charity_project_id, self.session
        )
        if charity_project is None:
            raise HTTPException(
                status_code=404,
                detail='Проект не найден!',
            )
        return charity_project

    async def check_project_before_update(
        self, charity_project: CharityProject, obj_in: CharityProjectUpdate
    ) -> None:
        if charity_project.fully_invested:
            raise HTTPException(
                status_code=400, detail='Закрытый проект нельзя редактировать!'
            )
        if obj_in.full_amount:
            if obj_in.full_amount < charity_project.invested_amount:
                raise HTTPException(
                    status_code=400,
                    detail='Нельзя установить сумму меньше вложенной',
                )

    async def charity_project_create(self, charity_project: CharityProjectCreate):
        await self.check_name_duplicate(charity_project.name)
        new_charity_project = await charity_project_crud.create(
            charity_project, self.session
        )

        await CharityProjectService.investing_process(
            new_charity_project, self.session
        )

        return new_charity_project

    async def charity_project_update(
        self, charity_project_id: int, obj_in: CharityProjectUpdate
    ):
        charity_project = await self.get_charity_project(charity_project_id)
        if obj_in.name:
            await self.check_name_duplicate(obj_in.name)

        await self.check_project_before_update(charity_project, obj_in)
        charity_project = await charity_project_crud.update(
            charity_project, obj_in, self.session
        )
        return charity_project

    async def create_donation_obj(
        self, donation, user: Optional[User] = None
    ):
        new_donation = await donation_crud.create(donation, self.session, user)
        await CharityProjectService.investing_process(new_donation, self.session)
        return new_donation

    @staticmethod
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
