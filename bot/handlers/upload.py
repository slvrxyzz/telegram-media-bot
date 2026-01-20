from __future__ import annotations

import os
from pathlib import Path

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

from bot.config import get_admin_ids, get_settings
from bot.db.models import MediaContent, Tag
from bot.db.session import get_session
from bot.states.upload import UploadStates
from bot.utils.tags import extract_tags


router = Router()


@router.message(Command("upload"))
async def upload_start(message: Message, state: FSMContext) -> None:
    await state.set_state(UploadStates.waiting_for_media)
    await message.answer("Шаг 1/2: отправьте одно фото или видео. /cancel — отмена.")


@router.message(Command("cancel"))
async def upload_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Загрузка отменена. Можете начать заново: /upload")


@router.message(UploadStates.waiting_for_media)
async def receive_media(message: Message, state: FSMContext) -> None:
    if message.photo:
        file_id = message.photo[-1].file_id
        file_unique_id = message.photo[-1].file_unique_id
        media_type = "photo"
    elif message.video:
        file_id = message.video.file_id
        file_unique_id = message.video.file_unique_id
        media_type = "video"
    else:
        await state.clear()
        await message.answer("Нужен именно фото или видео. Процесс отменен.")
        return

    await state.update_data(
        file_id=file_id,
        file_unique_id=file_unique_id,
        media_type=media_type,
    )
    await state.set_state(UploadStates.waiting_for_description)
    await message.answer("Шаг 2/2: отправьте текстовое описание. /cancel — отмена.")


@router.message(UploadStates.waiting_for_description)
async def receive_description(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Нужно текстовое описание. Отправьте текст.")
        return

    data = await state.get_data()
    tags = extract_tags(message.text)
    local_path: str | None = None

    settings = get_settings()
    if settings.download_files:
        local_path = await _download_media(
            bot=message.bot,
            file_id=data["file_id"],
            file_unique_id=data["file_unique_id"],
            media_type=data["media_type"],
            base_path=settings.download_path,
        )

    is_approved = not settings.moderation_enabled
    async_session = get_session()
    async with async_session() as session:
        media = MediaContent(
            telegram_file_id=data["file_id"],
            telegram_file_unique_id=data["file_unique_id"],
            media_type=data["media_type"],
            description=message.text,
            local_path=local_path,
            is_approved=is_approved,
        )
        if tags:
            existing = await session.execute(select(Tag).where(Tag.name.in_(tags)))
            existing_tags = {tag.name: tag for tag in existing.scalars().all()}
            for tag_name in tags:
                media.tags.append(existing_tags.get(tag_name) or Tag(name=tag_name))

        session.add(media)
        await session.commit()

    await state.clear()
    if is_approved:
        await message.answer("Контент сохранен.")
    else:
        await message.answer("Контент сохранен и отправлен на модерацию.")

    await _notify_admins(message, settings, media_id=media.id, description=message.text)


async def _notify_admins(message: Message, settings, media_id: int, description: str) -> None:
    if not settings.moderation_enabled:
        return
    admin_ids = get_admin_ids(settings)
    if not admin_ids:
        return
    preview = description.strip().replace("\n", " ")
    if len(preview) > 60:
        preview = preview[:57] + "..."
    text = f"Новая запись на модерации: {media_id}\n{preview}\n/approve {media_id}"
    for admin_id in admin_ids:
        try:
            await message.bot.send_message(admin_id, text)
        except Exception:
            continue


async def _download_media(
    bot,
    file_id: str,
    file_unique_id: str,
    media_type: str,
    base_path: str,
) -> str:
    Path(base_path).mkdir(parents=True, exist_ok=True)
    ext = "jpg" if media_type == "photo" else "mp4"
    target_path = os.path.join(base_path, f"{file_unique_id}.{ext}")
    await bot.download(file_id, destination=target_path)
    return target_path

