"""
Test Suite: Core functionality tests for Bengali PDF Search System.
Uses pytest-asyncio for async test support.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Override settings BEFORE importing app
import os
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-for-testing"
os.environ["SECRET_KEY"] = "test-app-secret-key-for-testing"

from app.db.database import Base, get_db
from main import app


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ─── Auth Tests ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_first_user_becomes_admin(client):
    res = await client.post("/api/auth/register", json={
        "email": "admin@test.com",
        "username": "admin",
        "password": "testpass123",
    })
    assert res.status_code == 201
    data = res.json()
    assert data["role"] == "admin"
    assert data["email"] == "admin@test.com"


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    await client.post("/api/auth/register", json={
        "email": "dup@test.com", "username": "dup1", "password": "testpass123"
    })
    res = await client.post("/api/auth/register", json={
        "email": "dup@test.com", "username": "dup2", "password": "testpass123"
    })
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_login_returns_tokens(client):
    await client.post("/api/auth/register", json={
        "email": "user@test.com", "username": "testuser", "password": "testpass123"
    })
    res = await client.post("/api/auth/login", json={
        "email": "user@test.com", "password": "testpass123"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_password(client):
    await client.post("/api/auth/register", json={
        "email": "user2@test.com", "username": "testuser2", "password": "correct123"
    })
    res = await client.post("/api/auth/login", json={
        "email": "user2@test.com", "password": "wrongpass"
    })
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_me_endpoint(client):
    await client.post("/api/auth/register", json={
        "email": "me@test.com", "username": "meuser", "password": "testpass123"
    })
    login_res = await client.post("/api/auth/login", json={
        "email": "me@test.com", "password": "testpass123"
    })
    token = login_res.json()["access_token"]
    res = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["email"] == "me@test.com"


# ─── Stats Tests ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stats_requires_auth(client):
    res = await client.get("/api/stats")
    assert res.status_code == 403  # No token


@pytest.mark.asyncio
async def test_stats_returns_data(client):
    await client.post("/api/auth/register", json={
        "email": "stats@test.com", "username": "statsuser", "password": "testpass123"
    })
    login_res = await client.post("/api/auth/login", json={
        "email": "stats@test.com", "password": "testpass123"
    })
    token = login_res.json()["access_token"]
    res = await client.get("/api/stats", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert "total_documents" in data
    assert "total_records" in data


# ─── Search Tests ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_requires_auth(client):
    res = await client.get("/api/search?q=test")
    assert res.status_code == 403


# ─── Text Extractor Unit Tests ────────────────────────────────────────────────

def test_extract_voter_fields_basic():
    from app.services.text_extractor import extract_voter_fields

    sample = """
    নাম: মোহাম্মদ রহিম উদ্দিন
    পিতার নাম: আব্দুল করিম
    মাতার নাম: ফাতেমা বেগম
    জেলা: ঢাকা
    উপজেলা: সাভার
    ভোটার নম্বর: 1234567890
    জন্ম তারিখ: ০১-০১-১৯৮৫
    """
    fields = extract_voter_fields(sample)
    assert fields["name"] is not None
    assert "রহিম" in fields["name"]
    assert fields["district"] is not None
    assert "ঢাকা" in fields["district"]


def test_extract_birth_year():
    from app.services.text_extractor import extract_birth_year
    assert extract_birth_year("০১-০১-১৯৮৫") == 1985
    assert extract_birth_year("15/06/1990") == 1990
    assert extract_birth_year("no year here") is None


def test_normalize_bengali_digits():
    from app.services.text_extractor import normalize_bengali_digits
    assert normalize_bengali_digits("০১২৩৪৫৬৭৮৯") == "0123456789"


def test_has_bengali_content():
    from app.services.text_extractor import has_bengali_content
    assert has_bengali_content("আমার নাম রহিম")
    assert not has_bengali_content("My name is Rahim")
    assert has_bengali_content("Mixed নাম text")


def test_extraction_confidence_scoring():
    from app.services.text_extractor import calculate_extraction_confidence
    full = {"name": "রহিম", "father_name": "করিম", "voter_id": "123", "district": "ঢাকা", "upazila": "সাভার"}
    empty = {"name": None, "father_name": None, "voter_id": None, "district": None, "upazila": None}
    assert calculate_extraction_confidence(full) > calculate_extraction_confidence(empty)
    assert 0.0 <= calculate_extraction_confidence(full) <= 1.0


# ─── Health Check ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_check(client):
    res = await client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"
