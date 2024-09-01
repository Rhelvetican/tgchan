import hydrogram
import time
from . import database
import asyncio
import os
import re
import random
import toml

from hydrogram import filters
from hydrogram.methods.utilities.idle import idle
from hydrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    Message,
)

config = toml.load("./config.toml")

# Initialize Client and Setup Memory

app = hydrogram.Client(
    name=config["general"]["name"],
    api_id=config["telegram"]["id"],
    api_hash=config["telegram"]["hash"],
    bot_token=config["telegram"]["token"],
)

p_app = hydrogram.Client(
    name="p_" + config["general"]["name"],
    api_id=config["telegram"]["id"],
    api_hash=config["telegram"]["hash"],
)

loop = asyncio.get_event_loop()
run = loop.run_until_complete

_ = run(app.start())
_ = run(p_app.start())

reply_mode: dict[str, int] = {}


# Define Core functions


def sanitize_str(string: str) -> str:
    ## Sanitizes the string by only allowing alphanumeric characters and hyphens

    return re.sub(pattern=r"[^a-zA-Z0-9-]", repl="", string=string)


def printlog(text: str) -> None:
    ## Prints the text to the console and logs it to a file

    print(text)

    if not os.path.exists("logs"):
        os.mkdir("logs")

    name = os.path.join("logs", time.strftime("%Y%m%d") + ".log")

    with open(file=name, mode="a") as f:
        _ = f.write(f"[{time.strftime("%Y-%m-%d %H:%M:%S")}] {text}\n")


# Define Callback Functions


@app.on_message(filters=filters.command(commands=["start"]))
async def start(_, message: Message) -> None:
    if len(message.command) == 1:
        ## Intro Function

        _ = await message.reply_text(
            text="Hello there! I am TG-Chan Posting Bot. I can help you post anonymous messages to TG-Chan.\n\nTo get started, just send me a message to post on TG-Chan, to reply to an existing post, you can just click on the reply button on that post and send me a reply message\n\nYou can view the privacy policy using the /privacy command."
        )

    elif len(message.command) == 2:
        ## Media Function

        file_path = "media/" + sanitize_str(string=message.command[1])

        if file_path.endswith("-jpg"):
            file_path = file_path[:-4] + ".jpg"
            extension = "jpg"
        elif file_path.endswith("-mp4"):
            file_path = file_path[:-4] + ".mp4"
            extension = "mp4"
        else:
            extension = None

        if not os.path.exists(file_path):
            _ = await message.reply_text(
                text=("Invalid media key! Please try again with a valid media key.")
            )
            return

        if extension == "jpg":
            msg = _ = await message.reply_photo(
                photo=file_path,
                caption=(
                    f"Here is the photo you requested. It will be deleted in {config["media"]["autoPurge"]} seconds."
                    if config["media"]["autoPurge"]
                    else "Here is the photo you requested."
                ),
            )

        elif extension == "mp4":
            msg = _ = await message.reply_video(
                video=file_path,
                caption=(
                    f"Here is the video you requested. It will be deleted in {config["media"]["autoPurgeInterval"]} seconds."
                    if config["media"]["autoPurge"]
                    else "Here is the video you requested."
                ),
            )

        if config["media"]["autoPurge"]:
            _ = await asyncio.sleep(config["media"]["autoPurgeInterval"])
            try:
                _ = await msg.delete()
            except Exception:
                return
    else:
        _ = await message.reply_text(text=("Invalid syntax!"))


@app.on_message(
    filters=filters.private
    & ~filters.command(commands=["start", "delete", "privacy", "cancel"])
)
async def post(client: hydrogram.Client, message: Message) -> None:
    ## Post Function

    uhash = database.hash(num=message.from_user.id)
    text = "When you're ready, just click on the button down below to post your reply to TG-Chan!"

    if uhash in reply_mode:
        msg = _ = await client.get_messages(
            chat_id=config["database"]["post"],
            message_ids=reply_mode[uhash],
        )

        text += f"\n\nCurrently replying to the following message: {msg.link}"

    _ = await message.reply_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Post",
                        callback_data="post",
                    ),
                ],
            ],
        ),
        reply_to_message_id=message.id,
    )


@app.on_message(filters=filters.command(commands=["delete"]))
async def delete(client: hydrogram.Client, message: Message) -> None:
    db = database.load()

    if len(message.command) != 3:
        _ = await message.reply_text(text=("Invalid syntax!"))
        return

    elif (
        not message.command[1].isdigit()
        or not message.command[2].replace("-", "").isnumeric()
    ):
        _ = await message.reply_text(text=("Invalid command!"))
        return

    try:
        msg = _ = await client.get_messages(
            chat_id=config["database"]["post"],
            message_ids=int(message.command[1]),
        )

        shash = db["posts"][msg.id]["shash"]
    except Exception:
        _ = await message.reply_text(
            text=("Invalid message id! Please try again with a valid message id.")
        )

        return

    if (
        shash != database.hash(num=message.from_user.id + int(message.command[2]) - config["database"]["seed"])
        and message.from_user.id != config["database"]["owner"]
    ):
        _ = await message.reply_text(
            text=(
                "You are not authorized to delete this message! Please try again with a valid message id."
            )
        )

        return

    _ = await p_app.delete_messages(
        chat_id=config["database"]["post"],
        message_ids=msg.id,
    )

    database.remove_post(db=db, id=msg.id)

    _ = await message.reply_text(text=("The message has been successfully deleted!"))

    printlog(f"User {shash} deleted a message with id {msg.id}!")

    database.save(db=db)


@app.on_message(filters=filters.command(commands=["privacy"]))
async def privacy(_: hydrogram.Client, message: Message) -> None:
    _ = await message.reply_text(
        text=(
            "Privacy Policy:\n\n"
            "1. Your messages are posted anonymously and are linked to your hash.\n"
            "2. Your user id is not stored or used for any purpose other than generating your hash.\n"
            "3. Your messages are not used for any other purpose than posting on TG-Chan.\n"
            "4. Your messages are not used to track you or your activities on the bot.\n"
            "5. Your hashes are generated in real-time for authentication and stored only for feedbacks.\n"
        ),
    )


@app.on_callback_query()
async def callback(client: hydrogram.Client, callback: CallbackQuery) -> None:
    db = database.load()
    uhash = database.hash(num=callback.from_user.id)

    if callback.data == "like":
        if callback.message.id not in db["posts"]:
            _ = await callback.answer(text="Invalid message!")
            return

        if uhash in db["posts"][callback.message.id]["feedbacks"]:
            if (
                db["posts"][callback.message.id]["feedbacks"][uhash]
                == database.Feedback.LIKE
            ):
                dislike = 0
                like = -1
                db["posts"][callback.message.id]["rating"] -= 1
            else:
                db["posts"][callback.message.id]["rating"] += 2
                dislike = -1
                db["posts"][callback.message.id]["feedbacks"][uhash] = (
                    database.Feedback.LIKE
                )
                like = 1
        else:
            db["posts"][callback.message.id]["rating"] += 1
            dislike = 0
            db["posts"][callback.message.id]["feedbacks"][uhash] = (
                database.Feedback.LIKE
            )
            like = 1

        existing_reply_markup = callback.message.reply_markup.inline_keyboard

        for row in existing_reply_markup:
            for button in row:
                if button.text.startswith("👍"):
                    current = int(button.text.split(" : ")[1])
                    button.text = (
                        f"👍 : {current + like}" if current + like >= 0 else "👍 : 0"
                    )
                elif button.text.startswith("👎"):
                    current = int(button.text.split(" : ")[1])
                    button.text = (
                        f"👎 : {current + dislike}"
                        if current + dislike >= 0
                        else "👎 : 0"
                    )

        try:
            _ = await callback.message.edit_reply_markup(
                reply_markup=InlineKeyboardMarkup(inline_keyboard=existing_reply_markup)
            )
        except Exception:
            pass

        if (
            db["posts"][callback.message.id]["rating"]
            >= config["policies"]["autoDeleteDislikeLimit"]
        ):
            if callback.message.id in db["autodelete"]:
                del db["autodelete"][callback.message.id]

        if (
            db["posts"][callback.message.id]["rating"]
            >= config["policies"]["pinLikeLimit"]
        ):
            _ = await callback.message.pin()

        if like == 1:
            _ = await callback.answer(text="Thanks for the feedback!")
        else:
            _ = await callback.answer(text="Feedback removed!")
            del db["posts"][callback.message.id]["feedbacks"][uhash]

    elif callback.data == "dislike":
        if callback.message.id not in db["posts"]:
            _ = await callback.answer(text="Invalid message!")
            return

        if uhash in db["posts"][callback.message.id]["feedbacks"]:
            if (
                db["posts"][callback.message.id]["feedbacks"][uhash]
                == database.Feedback.DISLIKE
            ):
                like = 0
                dislike = -1
                db["posts"][callback.message.id]["rating"] += 1
            else:
                db["posts"][callback.message.id]["rating"] -= 2
                like = -1
                dislike = 1
                db["posts"][callback.message.id]["feedbacks"][uhash] = (
                    database.Feedback.DISLIKE
                )
        else:
            db["posts"][callback.message.id]["rating"] -= 1
            like = 0
            dislike = 1
            db["posts"][callback.message.id]["feedbacks"][uhash] = (
                database.Feedback.DISLIKE
            )

        existing_reply_markup = callback.message.reply_markup.inline_keyboard

        for row in existing_reply_markup:
            for button in row:
                if button.text.startswith("👍"):
                    current = int(button.text.split(" : ")[1])
                    button.text = (
                        f"👍 : {current + like}" if current + like >= 0 else "👍 : 0"
                    )
                elif button.text.startswith("👎"):
                    current = int(button.text.split(" : ")[1])
                    button.text = (
                        f"👎 : {current + dislike}"
                        if current + dislike >= 0
                        else "👎 : 0"
                    )

        try:
            _ = await callback.message.edit_reply_markup(
                reply_markup=InlineKeyboardMarkup(inline_keyboard=existing_reply_markup)
            )
        except Exception:
            pass

        if (
            db["posts"][callback.message.id]["rating"]
            <= -config["policies"]["unpinDislikeLimit"]
        ):
            _ = await callback.message.unpin()

        if (
            db["posts"][callback.message.id]["rating"]
            <= -config["policies"]["deleteDislikeLimit"]
        ):
            if callback.message.id in db["autodelete"]:
                del db["autodelete"][callback.message.id]

            _ = await p_app.delete_messages(
                chat_id=config["database"]["post"],
                message_ids=callback.message.id,
            )
            database.remove_post(db=db, id=callback.message.id)

        if dislike == 1:
            _ = await callback.answer(text="Thanks for the feedback!")
        else:
            _ = await callback.answer(text="Feedback removed!")
            del db["posts"][callback.message.id]["feedbacks"][uhash]

    elif callback.data == "reply":
        if callback.message.id not in db["posts"]:
            _ = await callback.answer(text="Invalid message!")
            return

        reply_mode[uhash] = callback.message.id

        _ = await callback.answer(
            text="Reply mode activated! Please send your reply message via bot. You can exit reply mode by sending /cancel."
        )

        return

    elif callback.data == "post":
        ## Post Function

        uhash = database.hash(num=callback.from_user.id)

        if (
            uhash in db["timings"]
            and callback.from_user.id != config["database"]["owner"]
        ):
            if db["timings"][uhash] > time.time():
                _ = await callback.answer(
                    text=("Please wait for a while before posting another message!")
                )

                return
            else:
                del db["timings"][uhash]
        else:
            db["timings"][uhash] = time.time() + config["policies"]["postInterval"]

        seed = random.randint(a=-999_999, b=999_999)
        shash = database.hash(num=callback.from_user.id + seed)

        reply_id = reply_mode.pop(uhash) if uhash in reply_mode else None
        try:
            if reply_id is not None:
                _ = await client.get_messages(
                    chat_id=config["database"]["post"],
                    message_ids=reply_id,
                )
        except Exception as e:
            print(f"Error: {e}")
            _ = await callback.answer(
                text=("Invalid reply id! Please try again with a valid reply id.")
            )
            return

        if len(db["autodelete"]) >= config["policies"]["autoDeleteCount"]:
            if reply_id == db["autodelete"][0]:
                _ = await callback.answer(
                    "Reply message is in the auto-delete queue! Please try again with a different message."
                )
                del db["reply_mode"][uhash]

            msg_id = db["autodelete"].pop(0)
            database.remove_post(db=db, id=msg_id)

            printlog(text=f"Auto-deleting message with id {db['autodelete'][0]}!")

            _ = await p_app.delete_messages(
                chat_id=config["database"]["post"],
                message_ids=msg_id,
            )

        message = callback.message.reply_to_message

        if message.photo:
            if message.photo.file_size > config["media"]["maxImageSize"]:
                _ = await message.reply_text(
                    text=(
                        "The image size is too large! Please try again with a smaller/compressed image or add a link to the image instead."
                    )
                )

                database.save(db=db)
                return

            _ = await message.download(file_name=f"media/{shash}.jpg")

            msg = _ = await client.send_message(
                reply_to_message_id=reply_id,
                chat_id=config["database"]["post"],
                text=(
                    message.caption.markdown + f"\n\nHash: {shash}"
                    if message.caption
                    else f"\n\nHash: {shash}"
                ),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="View attached photo",
                                url=f"https://t.me/{config["telegram"]["username"]}?start={shash}-jpg",
                            ),
                        ],
                        [
                            InlineKeyboardButton(
                                text="👍 : 0",
                                callback_data="like",
                            ),
                            InlineKeyboardButton(
                                text="👎 : 0",
                                callback_data="dislike",
                            ),
                            InlineKeyboardButton(
                                text="Reply",
                                callback_data="reply",
                            ),
                        ],
                    ],
                ),
            )

            database.add_post(db=db, id=msg.id, media=f"media/{shash}.jpg", shash=shash)

        elif message.video:
            if message.video.file_size > config["telegram"]["maxVideoSize"]:
                _ = await message.reply_text(
                    text=(
                        "The video size is too large! Please try again with a smaller/compressed video or add a link to the video instead."
                    )
                )

                database.save(db=db)
                return

            _ = await message.download(file_name=f"media/{shash}.mp4")

            msg = _ = await client.send_message(
                reply_to_message_id=reply_id,
                chat_id=config["database"]["post"],
                text=(
                    message.caption.markdown + f"\n\nHash: {shash}"
                    if message.caption
                    else f"\n\nHash: {shash}"
                ),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="View attached video",
                                url=f"https://t.me/{config["telegram"]["username"]}?start={shash}-mp4",
                            ),
                        ],
                        [
                            InlineKeyboardButton(
                                text="👍 : 0",
                                callback_data="like",
                            ),
                            InlineKeyboardButton(
                                text="👎 : 0",
                                callback_data="dislike",
                            ),
                            InlineKeyboardButton(
                                text="Reply",
                                callback_data="reply",
                            ),
                        ],
                    ],
                ),
            )

            database.add_post(db=db, id=msg.id, media=f"media/{shash}.mp4", shash=shash)

        elif message.text:
            msg = _ = await client.send_message(
                reply_to_message_id=reply_id,
                chat_id=config["database"]["post"],
                text=message.text.markdown + f"\n\nHash: {shash}",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="👍 : 0",
                                callback_data="like",
                            ),
                            InlineKeyboardButton(
                                text="👎 : 0",
                                callback_data="dislike",
                            ),
                            InlineKeyboardButton(
                                text="Reply",
                                callback_data="reply",
                            ),
                        ],
                    ],
                ),
            )

            database.add_post(db=db, id=msg.id, shash=shash)

        else:
            _ = await message.reply_text(
                text=(
                    "Invalid message type! Please try again with a valid message type."
                )
            )

            database.save(db=db)
            return

        db["autodelete"].append(msg.id)

        _ = await callback.message.edit_text(
            text=(
                f"Your [message](https://t.me/{config["database"]["postUsername"]}/{msg.id}) has been successfully posted!\n\nTo delete your post, use the `/delete {msg.id} {seed + config['database']['seed']}` command."
            )
        )

        printlog(f"{uhash} posted a message with id {msg.id}!")

    else:
        _ = await callback.answer(text="Invalid action!")

        database.save(db=db)
        return

    database.save(db=db)


@app.on_message(filters=filters.command(commands=["cancel"]))
async def cancel(_: hydrogram.Client, message: Message) -> None:
    uhash = database.hash(num=message.from_user.id)

    if uhash in reply_mode:
        del reply_mode[uhash]
        _ = await message.reply_text(text="Reply mode deactivated!")
    else:
        _ = await message.reply_text(text="You are not in reply mode!")


# Run the Bot
print("Bot is running!")

run(idle())

run(app.stop())
run(p_app.stop())
