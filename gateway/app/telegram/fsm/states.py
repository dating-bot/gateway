from aiogram.fsm.state import State, StatesGroup


class RegistrationState(StatesGroup):
    """FSM состояния для 5-шагового создания профиля."""

    enter_name = State()
    enter_age = State()
    enter_city = State()
    enter_bio = State()
    enter_gender = State()


class EditProfileState(StatesGroup):
    """Редактирование одного поля: выбор поля (inline) → ввод значения."""

    enter_value = State()


class PhotoPromptState(StatesGroup):
    """Ожидание фото от пользователя."""

    waiting_photo = State()


class PhotoManageState(StatesGroup):
    """Добавление фото из меню редактирования."""

    waiting_photo = State()


class PreferencesState(StatesGroup):
    """Настройки предпочтений: gender_pref → age_min → age_max → max_distance."""

    enter_gender_pref = State()
    enter_age_min = State()
    enter_age_max = State()
    enter_max_distance = State()
