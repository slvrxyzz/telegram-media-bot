from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from bot.handlers.query import browse_media, send_ids_page
from bot.handlers.upload import upload_cancel, upload_start
from bot.states.actions import ActionStates


router = Router()

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📤 Загрузить"), KeyboardButton(text="🖼️ Лента")],
        [KeyboardButton(text="🏷️ Фильтр"), KeyboardButton(text="🔤 Поиск")],
        [KeyboardButton(text="🔎 Список ID"), KeyboardButton(text="🧾 Найти по ID")],
        [KeyboardButton(text="✏️ Редактировать"), KeyboardButton(text="🗑️ Удалить")],
        [KeyboardButton(text="📚 Помощь"), KeyboardButton(text="🏠 Меню")],
        [KeyboardButton(text="❌ Отменить")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Нажмите кнопку или напишите команду",
)


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    await message.answer(
        "<b>Добро пожаловать!</b> ✨\n"
        "Я сохраняю фото/видео с описанием и умею искать по тегам и датам.\n"
        "Выберите кнопку ниже или напишите команду вручную.",
        reply_markup=MAIN_KEYBOARD,
    )


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    await message.answer(
        "<b>Короткая шпаргалка</b> 📌\n"
        "📤 /upload — отправьте фото или видео, затем описание\n"
        "🖼️ /list — листать записи с фото/видео\n"
        "🔎 /ids [page] — список ID\n"
        "🧾 /get &lt;id&gt; — медиа и описание\n"
        "🏷️ /filter #tag days=7 page=2\n"
        "🏷️ /filter #tag from=2025-01-01 to=2025-01-19 page=2\n"
        "🔤 /search &lt;слово&gt; — поиск по описанию\n"
        "✏️ /edit &lt;id&gt; &lt;новое описание&gt;\n"
        "🗑️ /delete &lt;id&gt; — удалить запись\n"
        "✅ /approve &lt;id&gt; — одобрить (для админов)\n"
        "❌ /cancel — отменить загрузку",
        reply_markup=MAIN_KEYBOARD,
    )


@router.message(Command("menu"))
async def menu_handler(message: Message) -> None:
    await message.answer(
        "Главное меню 🧭",
        reply_markup=MAIN_KEYBOARD,
    )


@router.message(lambda m: m.text == "📤 Загрузить")
async def menu_upload(message: Message, state: FSMContext) -> None:
    await upload_start(message, state)


@router.message(lambda m: m.text == "🖼️ Лента")
async def menu_browse(message: Message) -> None:
    await browse_media(message)


@router.message(lambda m: m.text == "🔎 Список ID")
async def menu_ids(message: Message) -> None:
    await send_ids_page(message, page=1)


@router.message(lambda m: m.text == "🧾 Найти по ID")
async def menu_get_hint(message: Message, state: FSMContext) -> None:
    await state.set_state(ActionStates.waiting_get_id)
    await message.answer("Введите ID записи (например: 12).")


@router.message(lambda m: m.text == "🏷️ Фильтр")
async def menu_filter_hint(message: Message, state: FSMContext) -> None:
    await state.set_state(ActionStates.waiting_filter_args)
    await message.answer(
        "Введите параметры фильтра, например:\n"
        "#cats days=7\n"
        "#cats #travel from=2025-01-01 to=2025-01-19"
    )


@router.message(lambda m: m.text == "🔤 Поиск")
async def menu_search_hint(message: Message, state: FSMContext) -> None:
    await state.set_state(ActionStates.waiting_search_text)
    await message.answer("Введите слово или фразу для поиска.")


@router.message(lambda m: m.text == "✏️ Редактировать")
async def menu_edit_hint(message: Message, state: FSMContext) -> None:
    await state.set_state(ActionStates.waiting_edit_id)
    await message.answer("Введите ID записи для редактирования.")


@router.message(lambda m: m.text == "🗑️ Удалить")
async def menu_delete_hint(message: Message, state: FSMContext) -> None:
    await state.set_state(ActionStates.waiting_delete_id)
    await message.answer("Введите ID записи для удаления.")


@router.message(lambda m: m.text == "📚 Помощь")
async def menu_help(message: Message) -> None:
    await help_handler(message)


@router.message(lambda m: m.text == "❌ Отменить")
async def menu_cancel(message: Message, state: FSMContext) -> None:
    await upload_cancel(message, state)


@router.message(lambda m: m.text == "🏠 Меню")
async def menu_show(message: Message) -> None:
    await menu_handler(message)

