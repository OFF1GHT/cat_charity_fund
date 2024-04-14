from fastapi import HTTPException

from app.crud.charity_project import charity_project_crud
from app.models import CharityProject
from app.schemas.charity_project import (
    CharityProjectUpdate,
    CharityProjectCreate,
)
from app.services.invested import investing_process


class CharityProjectService:
    def __init__(self, session):
        self.session = session

    async def check_name_duplicate(
            self,
            charity_project_name: str,
    ) -> None:
        charity_project_id = await charity_project_crud.get_project_id_by_name(
            charity_project_name, self.session
        )
        if charity_project_id is not None:
            raise HTTPException(
                status_code=400, detail='Проект с таким именем уже существует!'
            )

    async def get_charity_project(
            self,
            charity_project_id: int,
    ) -> CharityProject:
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

    async def charity_project_create(
            self, charity_project: CharityProjectCreate
    ):
        await self.check_name_duplicate(charity_project.name)
        new_charity_project = await charity_project_crud.create(
            charity_project, self.session
        )

        await investing_process(new_charity_project,
                                self.session)

        return new_charity_project

    async def charity_project_update(
            self,
            charity_project_id: int,
            obj_in: CharityProjectUpdate,
    ):
        charity_project = await self.get_charity_project(
            charity_project_id
        )
        if obj_in.name:
            await self.check_name_duplicate(obj_in.name)

        await self.check_project_before_update(charity_project, obj_in)
        charity_project = await charity_project_crud.update(
            charity_project, obj_in, self.session
        )
        return charity_project