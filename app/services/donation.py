from typing import Optional

from app.crud.donation import donation_crud
from app.models import User
from app.services.invested import investing_process


class DonationService:
    def __init__(self, session):
        self.session = session

    async def create_donation_obj(self, donation, user: Optional[User] = None):
        new_donation = await donation_crud.create(donation, self.session, user)
        await investing_process(new_donation, self.session)
        await self.session.commit()
        await self.session.refresh(donation)
        return new_donation