from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📷 Добавить еду",
                    callback_data="add_food"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Сегодня",
                    callback_data="today"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚙️ Настройки",
                    callback_data="settings"
                )
            ]
        ]
    )


def cancel_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="cancel_action"
                )
            ]
        ]
    )


def amount_type_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚖️ Граммы / мл",
                    callback_data="amount_grams"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🥣 Порции",
                    callback_data="amount_portion"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="cancel_action"
                )
            ]
        ]
    )


def confirm_meal():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Добавить",
                    callback_data="meal_confirm"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="meal_cancel"
                )
            ]
        ]
    )


def today_keyboard(protein_shakes: int = 0):
    """
    Клавиатура экрана 'Сегодня'.

    protein_shakes:
    0 = протеин не выпит
    1 = выпит один стакан
    2 = выпиты оба стакана
    """

    protein_shakes = max(
        0,
        min(protein_shakes, 2)
    )

    if protein_shakes == 0:
        protein_text = "🥤 Выпить протеин 0/2"
    elif protein_shakes == 1:
        protein_text = "🥤 Выпить протеин 1/2"
    else:
        protein_text = "🥤 Протеин 2/2"

    buttons = []

    # Кнопка протеина всегда отображается.
    # После 2 стаканов она становится просто неактивной.
    buttons.append(
        [
            InlineKeyboardButton(
                text=protein_text,
                callback_data="add_protein"
            )
        ]
    )

    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Удалить последний приём",
                callback_data="delete_last"
            )
        ]
    )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔄 Обновить",
                callback_data="today"
            )
        ]
    )

    buttons.append(
        [
            InlineKeyboardButton(
                text="⬅️ Главное меню",
                callback_data="back_main"
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


def settings_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔥 Изменить калории",
                    callback_data="set_calories"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🥩 Изменить белок",
                    callback_data="set_protein"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🥑 Изменить жиры",
                    callback_data="set_fat"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🍞 Изменить углеводы",
                    callback_data="set_carbs"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="back_main"
                )
            ]
        ]
    )
