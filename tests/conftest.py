import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import get_db
from app.main import app as fastapi_app
from app.middleware.rate_limit import RateLimitMiddleware

# Register all database models.
import app.models


@pytest.fixture(scope="function")
def test_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)

    yield engine

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine):
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )

    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def client(test_engine):
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db

    # Reset rate-limit history before each test.
    for middleware in fastapi_app.user_middleware:
        if middleware.cls == RateLimitMiddleware:
            break

    # Find the active rate limiter and clear its request history.
    middleware_stack = fastapi_app.middleware_stack
    while middleware_stack is not None:
        if isinstance(middleware_stack, RateLimitMiddleware):
            with middleware_stack.lock:
                middleware_stack.requests.clear()
            break

        middleware_stack = getattr(middleware_stack, "app", None)

    with TestClient(fastapi_app) as test_client:
        yield test_client

    fastapi_app.dependency_overrides.clear()