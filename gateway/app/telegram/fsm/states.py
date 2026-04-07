from aiogram.fsm.state import State, StatesGroup


class RegistrationState(StatesGroup):
    """FSM состояния для 5-шагового создания профиля."""

    enter_name = State()
    enter_age = State()
    enter_city = State()
    enter_bio = State()
    enter_gender = State()


class EditProfileState(StatesGroup):
    """FSM состояния для редактирования поля профиля."""

    choose_field = State()
    enter_value = State()


class PhotoPromptState(StatesGroup):
    """Ожидание фото от пользователя."""

    waiting_photo = State()
