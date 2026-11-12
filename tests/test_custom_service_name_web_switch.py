"""The platform's «نام دلخواه سرویس» switch in the web naming tab; shops never see or store it."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.services.custom_service_name import SETTING_KEY, name_step_enabled
from app.services.users import clear_settings_cache, get_all_settings
from tests.test_update_owner_only import OWNER_SESSION, SHOP_SESSION, RoutesHarness

FIELD = f"s_{SETTING_KEY}"
SHOP_ID = 5


class CustomServiceNameWebSwitchTests(RoutesHarness):
    async def form(self, payload: dict, path: str, data: dict[str, str]):
        cookie = f"session={self.signer.dumps(payload)}; csrf=token"
        headers = {"cookie": cookie, "x-csrf-token": "token", "origin": "http://panel.test"}
        return await self.client.post(path, headers=headers, data=data)

    async def stored(self, shop_id: int | None) -> str:
        clear_settings_cache()
        async with async_sessionmaker(self.engine, expire_on_commit=False)() as session:
            return (await get_all_settings(session, reseller_id=shop_id))[SETTING_KEY]

    async def test_the_owner_finds_the_switch_in_the_naming_tab(self) -> None:
        response = await self.call(OWNER_SESSION, "GET", "/settings?tab=naming")
        self.assertEqual(response.status_code, 200)
        self.assertIn(FIELD, response.text)
        self.assertIn("اسم تصادفی", response.text)

    async def test_the_owner_turns_the_name_step_on_and_off(self) -> None:
        response = await self.form(OWNER_SESSION, "/settings?tab=naming", {FIELD: "1", "s_pg_username_prefix": "clk"})
        self.assertEqual(response.status_code, 303)
        self.assertEqual(await self.stored(None), "1")
        async with async_sessionmaker(self.engine, expire_on_commit=False)() as session:
            self.assertTrue(await name_step_enabled(session, None))
        await self.form(OWNER_SESSION, "/settings?tab=naming", {"s_pg_username_prefix": "clk"})
        self.assertEqual(await self.stored(None), "0", "an unchecked switch turns the step off")

    async def test_a_shop_does_not_see_the_platform_switch(self) -> None:
        response = await self.call(SHOP_SESSION, "GET", "/shop-settings?tab=naming")
        self.assertEqual(response.status_code, 200)
        self.assertIn("s_pg_username_pattern", response.text)
        self.assertNotIn(FIELD, response.text)

    async def test_a_shop_cannot_store_the_switch_by_posting_it(self) -> None:
        response = await self.form(SHOP_SESSION, "/shop-settings?tab=naming", {FIELD: "1", "s_pg_username_prefix": "shp"})
        self.assertEqual(response.status_code, 303)
        self.assertEqual(await self.stored(SHOP_ID), "0")
        self.assertEqual(await self.stored(None), "0")
