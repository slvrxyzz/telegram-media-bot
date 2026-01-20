from __future__ import annotations

from datetime import datetime

from aiogram import Router
from aiogram.filters import Command
import html

from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo,
    Message,
)
from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

from bot.config import get_admin_ids, get_settings
from bot.db.models import MediaContent, Tag
from bot.db.session import get_session
from bot.states.actions import ActionStates
from bot.utils.parsing import parse_filter_args
from bot.utils.tags import extract_tags


router = Router()

PAGE_SIZE = 10
BROWSE_PAGE_SIZE = 1


@router.message(Command("list"))
async def browse_media(message: Message) -> None:
    await _send_browse_page(message, page=1)


@router.message(Command("ids"))
async def list_media_ids(message: Message) -> None:
    args = message.text.split(maxsplit=1)
    page = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1
    page = max(page, 1)
    await send_ids_page(message, page)


async def send_ids_page(message: Message, page: int) -> None:
    page = max(page, 1)

    settings = get_settings()
    is_admin = _is_admin(message, settings)
    async_session = get_session()
    async with async_session() as session:
        count_query = select(func.count(MediaContent.id))
        if not is_admin and settings.moderation_enabled:
            count_query = count_query.where(MediaContent.is_approved.is_(True))
        total = await session.scalar(count_query)
        total = total or 0
        offset = (page - 1) * PAGE_SIZE
        query = select(MediaContent).order_by(MediaContent.created_at.desc())
        if not is_admin and settings.moderation_enabled:
            query = query.where(MediaContent.is_approved.is_(True))
        query = query.offset(offset).limit(PAGE_SIZE)
        result = await session.execute(query)
        items = result.scalars().all()

    if not items:
        await message.answer("Список пуст.")
        return

    lines = []
    for item in items:
        preview = item.description.strip().replace("\n", " ")
        if len(preview) > 40:
            preview = preview[:37] + "..."
        created = item.created_at.strftime("%Y-%m-%d %H:%M")
        lines.append(f"<b>{item.id}</b> | {created} | {preview}")

    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    await message.answer(
        "<b>Список ID</b>:\n" + "\n".join(lines) + f"\nСтр. {page}/{pages}"
    )


@router.message(Command("get"))
async def get_media(message: Message) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("Использование: /get <id>")
        return

    media_id = int(args[1])
    await _send_media_by_id(message, media_id)


@router.message(ActionStates.waiting_get_id)
async def get_media_by_button(message: Message) -> None:
    if not message.text or not message.text.isdigit():
        await message.answer("Нужно число. Введите ID записи.")
        return
    media_id = int(message.text)
    await _send_media_by_id(message, media_id)


@router.message(Command("filter"))
async def filter_media(message: Message) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "Формат фильтра:\n"
            "/filter #tag days=7 page=1\n"
            "/filter #tag1 #tag2 from=2025-01-01 to=2025-01-19 page=1"
        )
        return

    params = parse_filter_args(args[1])
    if not (params.tags or params.start_dt or params.end_dt):
        await message.answer(
            "Нужно указать теги или даты.\n"
            "Пример: /filter #cats days=7\n"
            "Пример: /filter #cats from=2025-01-01 to=2025-01-19"
        )
        return

    await _run_filter(message, params)


@router.message(ActionStates.waiting_filter_args)
async def filter_media_by_button(message: Message, state) -> None:
    if not message.text:
        await message.answer("Введите параметры фильтра.")
        return
    params = parse_filter_args(message.text)
    await state.clear()
    if not (params.tags or params.start_dt or params.end_dt):
        await message.answer(
            "Нужно указать теги или даты.\n"
            "Пример: #cats days=7\n"
            "Пример: #cats from=2025-01-01 to=2025-01-19"
        )
        return
    await _run_filter(message, params)


@router.message(Command("search"))
async def search_media(message: Message) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /search <слово или фраза>")
        return
    query_text = args[1].strip()
    if not query_text:
        await message.answer("Введите слово или фразу для поиска.")
        return
    await _search_by_text(message, query_text)


@router.message(Command("delete"))
async def delete_media(message: Message) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("Использование: /delete <id>")
        return

    media_id = int(args[1])
    async_session = get_session()
    async with async_session() as session:
        media = await session.get(MediaContent, media_id)
        if not media:
            await message.answer("Запись не найдена.")
            return
        await session.delete(media)
        await session.commit()

    await message.answer("Запись удалена.")


@router.message(Command("edit"))
async def edit_media(message: Message) -> None:
    args = message.text.split(maxsplit=2)
    if len(args) < 3 or not args[1].isdigit():
        await message.answer("Использование: /edit <id> <новое описание>")
        return

    media_id = int(args[1])
    new_description = args[2].strip()
    if not new_description:
        await message.answer("Описание не должно быть пустым.")
        return
    await _edit_media_by_id(message, media_id, new_description)


async def _send_media_by_id(message: Message, media_id: int) -> None:
    settings = get_settings()
    is_admin = _is_admin(message, settings)
    async_session = get_session()
    async with async_session() as session:
        result = await session.execute(
            select(MediaContent)
            .options(selectinload(MediaContent.tags))
            .where(MediaContent.id == media_id)
        )
        media = result.scalar_one_or_none()

    if not media:
        await message.answer("Запись не найдена.")
        return
    if settings.moderation_enabled and not is_admin and not media.is_approved:
        await message.answer("Запись на модерации.")
        return

    await _send_media(message, media, is_admin=is_admin)


async def _run_filter(message: Message, params) -> None:
    settings = get_settings()
    is_admin = _is_admin(message, settings)
    async_session = get_session()
    async with async_session() as session:
        query = (
            select(MediaContent)
            .options(selectinload(MediaContent.tags))
            .order_by(MediaContent.created_at.desc())
        )
        count_query = select(func.count(func.distinct(MediaContent.id)))

        if params.tags:
            query = query.join(MediaContent.tags).where(Tag.name.in_(params.tags))
            count_query = count_query.join(MediaContent.tags).where(Tag.name.in_(params.tags))

        date_filters = []
        if params.start_dt:
            date_filters.append(MediaContent.created_at >= params.start_dt)
        if params.end_dt:
            date_filters.append(MediaContent.created_at <= params.end_dt)
        if date_filters:
            query = query.where(and_(*date_filters))
            count_query = count_query.where(and_(*date_filters))
        if not is_admin and settings.moderation_enabled:
            query = query.where(MediaContent.is_approved.is_(True))
            count_query = count_query.where(MediaContent.is_approved.is_(True))

        total = await session.scalar(count_query)
        total = total or 0
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(max(params.page, 1), pages)
        offset = (page - 1) * PAGE_SIZE
        result = await session.execute(query.offset(offset).limit(PAGE_SIZE))
        items = result.scalars().all()

    if not items:
        await message.answer("Ничего не найдено.")
        return

    lines = []
    for item in items:
        preview = item.description.strip().replace("\n", " ")
        if len(preview) > 40:
            preview = preview[:37] + "..."
        created = item.created_at.strftime("%Y-%m-%d %H:%M")
        lines.append(f"<b>{item.id}</b> | {created} | {preview}")

    await message.answer(
        "<b>Результаты</b>:\n" + "\n".join(lines) + f"\nСтр. {page}/{pages}"
    )


async def _search_by_text(message: Message, query_text: str) -> None:
    settings = get_settings()
    is_admin = _is_admin(message, settings)
    async_session = get_session()
    async with async_session() as session:
        query = (
            select(MediaContent)
            .options(selectinload(MediaContent.tags))
            .order_by(MediaContent.created_at.desc())
            .where(MediaContent.description.ilike(f"%{query_text}%"))
            .limit(PAGE_SIZE)
        )
        if not is_admin and settings.moderation_enabled:
            query = query.where(MediaContent.is_approved.is_(True))
        result = await session.execute(query)
        items = result.scalars().all()

    if not items:
        await message.answer("Ничего не найдено.")
        return

    lines = []
    for item in items:
        preview = item.description.strip().replace("\n", " ")
        if len(preview) > 40:
            preview = preview[:37] + "..."
        created = item.created_at.strftime("%Y-%m-%d %H:%M")
        lines.append(f"<b>{item.id}</b> | {created} | {preview}")

    await message.answer("<b>Результаты поиска</b>:\n" + "\n".join(lines))


async def _edit_media_by_id(message: Message, media_id: int, new_description: str) -> None:
    settings = get_settings()
    is_admin = _is_admin(message, settings)
    if settings.moderation_enabled and not is_admin:
        await message.answer("Редактирование доступно только администраторам.")
        return

    async_session = get_session()
    async with async_session() as session:
        media = await session.get(MediaContent, media_id)
        if not media:
            await message.answer("Запись не найдена.")
            return
        media.description = new_description
        new_tags = extract_tags(new_description)
        if new_tags:
            existing = await session.execute(select(Tag).where(Tag.name.in_(new_tags)))
            existing_tags = {tag.name: tag for tag in existing.scalars().all()}
            media.tags = [
                existing_tags.get(tag_name) or Tag(name=tag_name)
                for tag_name in new_tags
            ]
        else:
            media.tags = []
        if settings.moderation_enabled:
            media.is_approved = is_admin
        await session.commit()

    await message.answer("Описание обновлено.")


async def _send_delete_confirm(message: Message, media_id: int) -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"delete:{media_id}"),
                InlineKeyboardButton(text="❌ Нет", callback_data="delete_cancel"),
            ]
        ]
    )
    await message.answer(f"Удалить запись #{media_id}?", reply_markup=keyboard)


@router.message(ActionStates.waiting_edit_id)
async def edit_media_choose_id(message: Message, state) -> None:
    if not message.text or not message.text.isdigit():
        await message.answer("Нужно число. Введите ID записи.")
        return
    await state.update_data(edit_id=int(message.text))
    await state.set_state(ActionStates.waiting_edit_text)
    await message.answer("Введите новое описание.")


@router.message(ActionStates.waiting_edit_text)
async def edit_media_by_button(message: Message, state) -> None:
    if not message.text:
        await message.answer("Нужно текстовое описание.")
        return
    data = await state.get_data()
    media_id = data.get("edit_id")
    await state.clear()
    if not media_id:
        await message.answer("ID не найден. Начните заново.")
        return
    await _edit_media_by_id(message, media_id, message.text)


@router.message(ActionStates.waiting_delete_id)
async def delete_media_by_button(message: Message, state) -> None:
    if not message.text or not message.text.isdigit():
        await message.answer("Нужно число. Введите ID записи.")
        return
    media_id = int(message.text)
    await state.clear()
    await _send_delete_confirm(message, media_id)


@router.message(ActionStates.waiting_search_text)
async def search_media_by_button(message: Message, state) -> None:
    if not message.text:
        await message.answer("Нужно слово или фраза.")
        return
    await state.clear()
    await _search_by_text(message, message.text.strip())


@router.message(Command("approve"))
async def approve_media(message: Message) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("Использование: /approve <id>")
        return

    settings = get_settings()
    if not _is_admin(message, settings):
        await message.answer("Команда доступна только администраторам.")
        return

    media_id = int(args[1])
    async_session = get_session()
    async with async_session() as session:
        media = await session.get(MediaContent, media_id)
        if not media:
            await message.answer("Запись не найдена.")
            return
        media.is_approved = True
        await session.commit()

    await message.answer("Запись одобрена.")


async def _send_media(message: Message, media: MediaContent, is_admin: bool = False) -> None:
    caption = _build_caption(media)
    keyboard = _action_keyboard(media.id, is_admin)
    if media.local_path:
        file = FSInputFile(media.local_path)
        if media.media_type == "photo":
            await message.answer_photo(file, caption=caption, reply_markup=keyboard)
        else:
            await message.answer_video(file, caption=caption, reply_markup=keyboard)
        return

    if media.media_type == "photo":
        await message.answer_photo(media.telegram_file_id, caption=caption, reply_markup=keyboard)
    else:
        await message.answer_video(media.telegram_file_id, caption=caption, reply_markup=keyboard)


def _is_admin(message: Message, settings) -> bool:
    admin_ids = get_admin_ids(settings)
    return message.from_user is not None and message.from_user.id in admin_ids


def _browse_keyboard(
    page: int,
    total_pages: int,
    media_id: int,
    is_admin: bool,
) -> InlineKeyboardMarkup:
    buttons = []
    if page > 1:
        buttons.append(
            InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f"browse:{page - 1}")
        )
    if page < total_pages:
        buttons.append(
            InlineKeyboardButton(text="Следующая ➡️", callback_data=f"browse:{page + 1}")
        )
    action_buttons = _action_buttons(media_id, is_admin)
    rows = []
    if buttons:
        rows.append(buttons)
    if action_buttons:
        rows.append(action_buttons)
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(lambda c: c.data and c.data.startswith("browse:"))
async def browse_callback(callback: CallbackQuery) -> None:
    page = int(callback.data.split(":", 1)[1])
    await _send_browse_page(callback.message, page=page, callback=callback)


async def _send_browse_page(
    message: Message,
    page: int,
    callback: CallbackQuery | None = None,
) -> None:
    settings = get_settings()
    is_admin = message.from_user is not None and message.from_user.id in get_admin_ids(settings)

    async_session = get_session()
    async with async_session() as session:
        count_query = select(func.count(MediaContent.id))
        if not is_admin and settings.moderation_enabled:
            count_query = count_query.where(MediaContent.is_approved.is_(True))
        total = await session.scalar(count_query)
        total = total or 0
        pages = max(1, (total + BROWSE_PAGE_SIZE - 1) // BROWSE_PAGE_SIZE)
        page = min(max(page, 1), pages)
        offset = (page - 1) * BROWSE_PAGE_SIZE
        query = (
            select(MediaContent)
            .options(selectinload(MediaContent.tags))
            .order_by(MediaContent.created_at.desc())
        )
        if not is_admin and settings.moderation_enabled:
            query = query.where(MediaContent.is_approved.is_(True))
        query = query.offset(offset).limit(BROWSE_PAGE_SIZE)
        result = await session.execute(query)
        media_items = result.scalars().all()

    if not media_items:
        if callback:
            await _safe_edit_text(callback, "Список пуст.")
            await callback.answer()
        else:
            await message.answer("Список пуст.")
        return

    media = media_items[0]
    caption = _build_caption(media)
    keyboard = _browse_keyboard(page, pages, media.id, is_admin)

    if callback:
        media_input = _build_input_media(media, caption)
        try:
            await callback.message.edit_media(media=media_input, reply_markup=keyboard)
        except Exception:
            await callback.message.answer_media_group(
                [_build_input_media(media, caption)]
            )
        await callback.answer()
        return

    await _send_media_with_caption(message, media, caption, keyboard)




def _build_caption(media: MediaContent) -> str:
    created = media.created_at.strftime("%Y-%m-%d %H:%M")
    description = html.escape(media.description.strip())
    max_len = 900
    if len(description) > max_len:
        description = description[: max_len - 3] + "..."
    tags_line = ""
    if media.tags:
        tags = " ".join(f"#{html.escape(tag.name)}" for tag in media.tags)
        tags_line = f"\n<b>Теги:</b> {tags}"
    return (
        f"🗂️ <b>Запись #{media.id}</b>\n"
        f"🕒 {created}"
        f"{tags_line}\n"
        f"📝 {description}"
    )


def _build_input_media(media: MediaContent, caption: str):
    if media.local_path:
        file = FSInputFile(media.local_path)
        if media.media_type == "photo":
            return InputMediaPhoto(media=file, caption=caption, parse_mode="HTML")
        return InputMediaVideo(media=file, caption=caption, parse_mode="HTML")
    if media.media_type == "photo":
        return InputMediaPhoto(media=media.telegram_file_id, caption=caption, parse_mode="HTML")
    return InputMediaVideo(media=media.telegram_file_id, caption=caption, parse_mode="HTML")


async def _send_media_with_caption(
    message: Message,
    media: MediaContent,
    caption: str,
    keyboard: InlineKeyboardMarkup | None,
) -> None:
    if media.local_path:
        file = FSInputFile(media.local_path)
        if media.media_type == "photo":
            await message.answer_photo(file, caption=caption, reply_markup=keyboard)
        else:
            await message.answer_video(file, caption=caption, reply_markup=keyboard)
        return
    if media.media_type == "photo":
        await message.answer_photo(media.telegram_file_id, caption=caption, reply_markup=keyboard)
    else:
        await message.answer_video(media.telegram_file_id, caption=caption, reply_markup=keyboard)


def _action_buttons(media_id: int, is_admin: bool) -> list[InlineKeyboardButton]:
    buttons = [
        InlineKeyboardButton(text="🧾 ID", callback_data=f"show_id:{media_id}"),
    ]
    if is_admin:
        buttons.append(
            InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"confirm_delete:{media_id}")
        )
    return buttons


def _action_keyboard(media_id: int, is_admin: bool) -> InlineKeyboardMarkup | None:
    buttons = _action_buttons(media_id, is_admin)
    if not buttons:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


async def _safe_edit_text(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    message = callback.message
    if message is None:
        return
    if message.photo or message.video or message.document:
        await message.edit_caption(caption=text, reply_markup=reply_markup)
    else:
        await message.edit_text(text, reply_markup=reply_markup)


@router.callback_query(lambda c: c.data and c.data.startswith("show_id:"))
async def show_id_callback(callback: CallbackQuery) -> None:
    media_id = int(callback.data.split(":", 1)[1])
    await callback.answer(f"ID записи: {media_id}", show_alert=True)


@router.callback_query(lambda c: c.data and c.data.startswith("confirm_delete:"))
async def confirm_delete_callback(callback: CallbackQuery) -> None:
    media_id = int(callback.data.split(":", 1)[1])
    settings = get_settings()
    if not _is_admin(callback, settings):
        await callback.answer("Недостаточно прав.", show_alert=True)
        return
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"delete:{media_id}"),
                InlineKeyboardButton(text="❌ Нет", callback_data="delete_cancel"),
            ]
        ]
    )
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer()


@router.callback_query(lambda c: c.data == "delete_cancel")
async def delete_cancel_callback(callback: CallbackQuery) -> None:
    await callback.answer("Удаление отменено.")


@router.callback_query(lambda c: c.data and c.data.startswith("delete:"))
async def delete_callback(callback: CallbackQuery) -> None:
    media_id = int(callback.data.split(":", 1)[1])
    settings = get_settings()
    if not _is_admin(callback, settings):
        await callback.answer("Недостаточно прав.", show_alert=True)
        return

    async_session = get_session()
    async with async_session() as session:
        media = await session.get(MediaContent, media_id)
        if not media:
            await callback.answer("Запись не найдена.", show_alert=True)
            return
        await session.delete(media)
        await session.commit()

    await callback.message.edit_caption("🗑️ Запись удалена.")
    await callback.answer("Удалено.")

