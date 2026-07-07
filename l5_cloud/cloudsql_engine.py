"""L5 — point the SAME agent at Cloud SQL for PostgreSQL instead of SQLite.

The only thing that changes vs L4 is the connection. `DatabaseSessionService`
uses an ASYNC SQLAlchemy engine, so Cloud SQL needs the async `asyncpg` driver
(NOT the sync `pg8000`) via the Cloud SQL Python Connector.

Usage:
    pip/uv add: cloud-sql-python-connector[asyncpg]  asyncpg
    export DB_URL="postgresql+asyncpg://"     # driver reads this
    # then build the engine with a creator (see build_cloud_sql_url below) —
    # OR simplest: run on Agent Runtime, which gives managed sessions for free.

This file documents the wiring; wire it into driver.py's ss() when you have a
Cloud SQL instance. Not exercised in the local run.
"""
# import sqlalchemy
# from google.cloud.sql.connector import Connector, IPTypes
#
# INSTANCE = "PROJECT:REGION:INSTANCE"   # from `gcloud sql instances describe`
#
# def make_engine():
#     connector = Connector()
#     async def getconn():
#         return await connector.connect_async(
#             INSTANCE, "asyncpg",
#             user="onboarding", password="...", db="onboarding",
#             ip_type=IPTypes.PUBLIC,
#         )
#     return sqlalchemy.ext.asyncio.create_async_engine(
#         "postgresql+asyncpg://", async_creator=getconn)
#
# Then in driver.ss():  DatabaseSessionService(db_url="postgresql+asyncpg://",
#                                              async_creator=getconn)
#
# ⚠ VERIFY on your ADK version: the exact kwarg DatabaseSessionService forwards
#   to create_async_engine for a custom creator (async_creator vs creator).
