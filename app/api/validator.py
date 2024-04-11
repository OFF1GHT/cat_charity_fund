from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.charity_project import charity_project_crud
from app.models.charity_project import CharityProject
from app.schemas.charity_project import CharityProjectUpdate
from app.core.constant import MIN_AMOUNT


async def check_charity_project_exists(
    charity_project_id: int,
    session: AsyncSession,
) -> CharityProject:
    charity_project = await charity_project_crud.get(
        charity_project_id, session
    )
    if charity_project is None:
        raise HTTPException(
            status_code=404,
            detail='Проект не найден!',
        )
    return charity_project


async def check_name_duplicate(
    charity_project_name: str,
    session: AsyncSession,
) -> None:
    charity_project_id = await charity_project_crud.get_project_id_by_name(
        charity_project_name, session
    )
    if charity_project_id is not None:
        raise HTTPException(
            status_code=400, detail='Проект с таким именем уже существует!'
        )


async def check_charity_project_close_date(
    charity_project_id: int,
    session: AsyncSession,
) -> None:
    '''Проверка на то, что проект закрыт.'''
    charity_project = await charity_project_crud.get(
        charity_project_id, session
    )
    if charity_project.close_date is not None:
        raise HTTPException(
            status_code=400, detail='Закрытый проект нельзя редактировать!'
        )


async def check_invested_project_exists(
    charity_project_id: int,
    session: AsyncSession,
) -> CharityProject:
    charity_project = await charity_project_crud.get(
        charity_project_id, session
    )
    charity_project = await check_charity_project_exists(
        charity_project_id, session
    )
    if charity_project.invested_amount > MIN_AMOUNT:
        raise HTTPException(
            status_code=400,
            detail='В проект были внесены средства, не подлежит удалению!',
        )


async def check_charity_project_full_amount(
    charity_project: CharityProject, obj_in: CharityProjectUpdate
) -> None:
    '''Проверка на то, что требуемая сумма должна быть больше внесенной'''
    if obj_in.full_amount is not None:
        if obj_in.full_amount < charity_project.invested_amount:
            raise HTTPException(
                status_code=400,
                detail='Нельзя установить значение меньше уже вложенной суммы',
            )


async def check_charity_project_delete(
    charity_project_id: int,
    session: AsyncSession,
) -> CharityProject:
    '''Проверка на присутствие/отсутствие инвестиций в проекте.'''
    charity_project = await charity_project_crud.get(
        charity_project_id, session
    )
    charity_project = await check_charity_project_exists(
        charity_project_id, session
    )
    if charity_project.invested_amount > MIN_AMOUNT:
        raise HTTPException(
            status_code=400,
            detail='Проверка на присутствие/отсутствие инвестиций в проекте',
        )
    return charity_project
