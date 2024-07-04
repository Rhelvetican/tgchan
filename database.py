# Import core libraries

import pickle
import typing
import config
import hashlib

from functools import lru_cache


# Define Database Type


class DatabaseType(typing.TypedDict):
    like_ratio: typing.Dict[int, int]
    user_timings: typing.Dict[str, int]
    autodelete: typing.List[int]
    like_users: typing.Dict[int, typing.Set[str]]
    media: typing.Dict[int, str]


# Database Core Functions


def save(db: DatabaseType, name: str = config.DATABASE_FILE) -> None:
    with open(file=name, mode="wb") as f:
        pickle.dump(obj=db, file=f)


def load(name: str = config.DATABASE_FILE) -> DatabaseType:
    try:
        with open(file=name, mode="rb") as f:
            db: DatabaseType = pickle.load(file=f)
            return db

    except FileNotFoundError:
        db: DatabaseType = {
            "like_ratio": dict(),
            "user_timings": dict(),
            "autodelete": list(),
            "like_users": dict(),
            "media": dict()
        }

        save(db=db)

        return db


# Sugarcoated Functions


@lru_cache
def hash(num: int) -> str:
    return hashlib.md5(string=str(num + config.SEED).encode()).hexdigest()
