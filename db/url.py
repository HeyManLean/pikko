from os import getenv


def _build_db_url() -> str:
    host = getenv("DB_HOST", "localhost")
    port = getenv("DB_PORT", "5432")
    user = getenv("DB_USER", "ai")
    password = getenv("DB_PASS", "ai")
    database = getenv("DB_DATABASE", "ai")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{database}"


db_url = _build_db_url()
