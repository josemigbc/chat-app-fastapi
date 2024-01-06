TORTOISE_ORM = {
    "connections": {"default": "sqlite://db.sqlite3"},
    "apps": {
        "models": {
            "models": ["models"],
            "default_connection": "default",
        },
    },
}

TEST_TORTOISE_ORM = {
    "connections": {"default": "sqlite://db-test.sqlite3"},
    "apps": {
        "models": {
            "models": ["models"],
            "default_connection": "default",
        },
    },
}