"""API tests for version history, package detail and diffs."""

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database.repositories import campaigns, versions

PACKAGE_ONE = {
    "brief": {"product": "Aurelia"},
    "copy": {"variants": [{"headline": "Old headline"}]},
    "score": {"total": 76.0},
}
PACKAGE_TWO = {
    "brief": {"product": "Aurelia"},
    "copy": {"variants": [{"headline": "New headline"}]},
    "score": {"total": 82.0},
}


async def _seed_versions(
    factory: async_sessionmaker[AsyncSession],
) -> tuple[UUID, UUID]:
    async with factory() as session:
        campaign = await campaigns.create(session, idea="Version API test")
        first = await versions.create(
            session,
            campaign_id=campaign.id,
            package=PACKAGE_ONE,
            score=76.0,
        )
        await versions.create(
            session,
            campaign_id=campaign.id,
            package=PACKAGE_TWO,
            score=82.0,
            parent_version_id=first.id,
        )
        await session.commit()
        return campaign.id, first.id


async def test_list_versions_returns_history_oldest_first(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    campaign_id, _ = await _seed_versions(session_factory)

    response = await client.get(f"/api/v1/campaigns/{campaign_id}/versions")

    assert response.status_code == 200
    items = response.json()
    assert [item["version"] for item in items] == [1, 2]
    assert items[0]["parent_version_id"] is None
    assert items[1]["parent_version_id"] is not None
    assert items[0]["score"] == 76.0
    assert items[1]["score"] == 82.0
    assert items[0]["created_at"]


async def test_get_version_returns_the_full_package(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    campaign_id, _ = await _seed_versions(session_factory)

    response = await client.get(f"/api/v1/campaigns/{campaign_id}/versions/2")

    assert response.status_code == 200
    assert response.json() == PACKAGE_TWO


async def test_diff_lists_only_changed_fields(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    campaign_id, _ = await _seed_versions(session_factory)

    response = await client.get(f"/api/v1/campaigns/{campaign_id}/versions/1/diff/2")

    assert response.status_code == 200
    body = response.json()
    assert body["from"] == 1
    assert body["to"] == 2
    assert {change["path"] for change in body["changes"]} == {
        "copy.variants.0.headline",
        "score.total",
    }


async def test_diff_of_identical_versions_is_empty(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    campaign_id, _ = await _seed_versions(session_factory)

    response = await client.get(f"/api/v1/campaigns/{campaign_id}/versions/1/diff/1")

    assert response.status_code == 200
    assert response.json()["changes"] == []


@pytest.mark.parametrize("suffix", ["", "/1", "/1/diff/2"])
async def test_unknown_campaign_returns_404(
    client: AsyncClient,
    suffix: str,
) -> None:
    missing = uuid4()

    response = await client.get(f"/api/v1/campaigns/{missing}/versions{suffix}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.parametrize("suffix", ["/99", "/1/diff/99"])
async def test_unknown_version_returns_404(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    suffix: str,
) -> None:
    campaign_id, _ = await _seed_versions(session_factory)

    response = await client.get(f"/api/v1/campaigns/{campaign_id}/versions{suffix}")

    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "not_found"
    assert error["details"]["version"] == 99
