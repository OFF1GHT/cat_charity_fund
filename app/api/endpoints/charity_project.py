from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import HTTPException
from app.api.invested import investing_process
from app.api.validator import (
    check_charity_project_close_date,
    check_charity_project_delete,
    check_charity_project_exists,
    check_charity_project_full_amount,
    check_name_duplicate,
)
from app.core.db import get_async_session
from app.core.user import current_superuser
from app.crud.charity_project import charity_project_crud
from app.schemas.charity_project import (CharityProjectCreate,
                                         CharityProjectDB,
                                         CharityProjectUpdate)

router = APIRouter()


@router.post(
    '/',
    response_model=CharityProjectDB,
    response_model_exclude_none=True,
    dependencies=[Depends(current_superuser)],
)
async def post_charity_projects(
    charity_project: CharityProjectCreate,
    session: AsyncSession = Depends(get_async_session),
):
    if not charity_project.description:
        raise HTTPException(
            status_code=422, detail='Описание проекта обязательно'
        )

    await check_name_duplicate(charity_project.name, session)

    new_project = await charity_project_crud.create(charity_project, session)
    await investing_process(new_project, session)
    return new_project


@router.get(
    '/',
    response_model_exclude_none=True,
)
async def get_all_charity_projects(
    session: AsyncSession = Depends(get_async_session),
):
    all_project = await charity_project_crud.get_multi(session)
    return all_project


@router.patch(
    '/{project_id}',
    dependencies=[Depends(current_superuser)],
    response_model=CharityProjectDB,
)
async def update_charity_project(
    project_id: int,
    obj_in: CharityProjectUpdate,
    session: AsyncSession = Depends(get_async_session),
):
    charity_project = await check_charity_project_exists(project_id, session)

    await check_charity_project_full_amount(charity_project, obj_in)
    await check_charity_project_close_date(project_id, session)

    if obj_in.name is not None:
        await check_name_duplicate(obj_in.name, session)

    charity_project = await charity_project_crud.update(
        charity_project, obj_in, session
    )

    return charity_project


@router.delete(
    '/{project_id}',
    dependencies=[Depends(current_superuser)],
    response_model=CharityProjectDB,
)
async def remove_charity_project(
    project_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    '''Удаление благотворительного проекта. Доступно для суперюзеров.'''
    charity_project = await check_charity_project_delete(project_id, session)
    charity_project = await charity_project_crud.remove(
        charity_project, session
    )
    return charity_project
