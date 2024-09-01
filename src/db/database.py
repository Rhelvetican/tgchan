# Import core libraries

import pickle
import typing
import os
import hashlib
import toml

from enum import Enum

config = toml.load("./config.toml")

# Define Database Schema

class Feedback(Enum):
    LIKE = 1
    DISLIKE = -1

    def __int__(self) -> int:
        return self.value


class PostType(typing.TypedDict):
    feedbacks: dict[str, Feedback]
    media: str | None
    shash: str
    rating: int


class DatabaseType(typing.TypedDict):
    posts: dict[int, PostType]
    timings: dict[str, int]
    autodelete: list[int]


# Database Core Functions

def save(db: DatabaseType, name: str = config['database']['file']) -> None:
    with open(file=name, mode="wb") as f:
        pickle.dump(obj=db, file=f)


def load(name: str = config['database']['file']) -> DatabaseType:
    try:
        with open(file=name, mode="rb") as f:
            db: DatabaseType = pickle.load(file=f)
            return db

    except FileNotFoundError:
        db: DatabaseType = {"posts": {}, "timings": {}, "autodelete": []}
        save(db=db)
        return db


# Sugarcoated Functions

def hash(num: int) -> str:
    return hashlib.md5(string=str(num + config['database']['seed']).encode()).hexdigest()

def add_post(db: DatabaseType, shash: str, id: int, media: str = None) -> None:
    if id in db["posts"]:
        return

    db["posts"][id] = {"feedbacks": {}, "media": media, "shash": shash, "rating": 0}


def remove_post(db: DatabaseType, id: int) -> None:
    if id not in db["posts"]:
        return

    if id in db["autodelete"]:
        db["autodelete"].remove(id)

    if db["posts"][id]["media"] is not None:
        try:
            os.remove(db["posts"][id]["media"])
        except FileNotFoundError:
            pass

    del db["posts"][id]
