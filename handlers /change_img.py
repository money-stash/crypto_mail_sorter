from aiogram import F, Router, Bot
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
import os

DATA_FILE = os.path.join("data", "data.json")
IMAGES_DIR = "images"
router = Router()


class ChangeImage(StatesGroup):
    waiting_for_photo = State()


def _cancel_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Cancel", callback_data="cancel_change_img")]
        ]
    )


@router.callback_query(
    F.data.in_(
        {
            "change_img_post1",
            "change_img_post2",
            "change_img_post3",
            "change_img_post4",
            "change_img_post5",
            "change_img_post6",
            "change_img_post7",
            "change_img_post8",
            "change_img_post9",
            "change_img_post10",
        }
    )
)
async def change_img_start(cb: CallbackQuery, state: FSMContext):
    try:
        post = int(cb.data.split("post")[-1])
    except ValueError:
        await cb.answer("Invalid post id", show_alert=True)
        return
    await state.update_data(post=post)
    await cb.message.answer(
        f"Send a new photo for post {post} or press Cancel.",
        reply_markup=_cancel_kb(),
    )
    await state.set_state(ChangeImage.waiting_for_photo)
    await cb.answer()


@router.message(ChangeImage.waiting_for_photo, F.photo)
async def change_img_save(msg: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    post = data.get("post")
    if not post:
        await msg.answer("Error: post number not found.")
        await state.clear()
        return
    photo = msg.photo[-1]
    filename = f"post{post}.jpg"
    path = os.path.join(IMAGES_DIR, filename)
    os.makedirs(IMAGES_DIR, exist_ok=True)
    await bot.download(photo, destination=path)
    await msg.answer(f"Image for post {post} has been updated ✅")
    await state.clear()


@router.callback_query(F.data == "cancel_change_img")
async def change_img_cancel(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.answer("Image change cancelled.")
    await cb.answer()


@router.message(F.text == "/cancel")
async def change_img_cancel_msg(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("Cancelled.")
