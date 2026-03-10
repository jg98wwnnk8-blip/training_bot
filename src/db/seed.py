import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Exercise, MuscleGroup

logger = logging.getLogger(__name__)

DEFAULT_GROUPS: list[tuple[str, str, int]] = [
    ("Грудь", "🔴", 1),
    ("Спина", "🔵", 2),
    ("Плечи", "🟡", 3),
    ("Бицепс", "🟢", 4),
    ("Трицепс", "🟠", 5),
    ("Ноги", "🟣", 6),
    ("Пресс", "⚪", 7),
    ("Кардио", "🏃", 8),
]

DEFAULT_EXERCISES: dict[str, list[str]] = {
    "Грудь": ["Жим лёжа", "Жим на наклонной", "Отжимания на брусьях"],
    "Спина": ["Подтягивания", "Тяга верхнего блока", "Тяга штанги в наклоне"],
    "Плечи": ["Жим гантелей сидя", "Махи в стороны"],
    "Бицепс": ["Подъём штанги на бицепс", "Молотки"],
    "Трицепс": ["Французский жим", "Разгибание на блоке"],
    "Ноги": ["Приседания со штангой", "Жим ногами", "Румынская тяга"],
    "Пресс": ["Скручивания", "Планка"],
    "Кардио": ["Беговая дорожка", "Велотренажёр"],
}


async def seed_system_catalog(session: AsyncSession) -> None:
    try:
        await session.rollback()
    except Exception:
        # If connection is already clean, ignore.
        pass

    try:
        existing = await session.scalar(
            select(MuscleGroup.id).where(MuscleGroup.user_id.is_(None)).limit(1)
        )
    except SQLAlchemyError:
        await session.rollback()
        logger.exception("Failed to check seed state")
        raise
    if existing:
        return

    groups_by_name: dict[str, MuscleGroup] = {}
    for name, emoji, order in DEFAULT_GROUPS:
        group = MuscleGroup(name=name, emoji=emoji, sort_order=order, is_custom=False, user_id=None)
        session.add(group)
        groups_by_name[name] = group
    await session.flush()

    for group_name, names in DEFAULT_EXERCISES.items():
        group = groups_by_name[group_name]
        for exercise_name in names:
            session.add(
                Exercise(
                    user_id=None,
                    muscle_group_id=group.id,
                    name=exercise_name,
                    is_custom=False,
                )
            )

    try:
        await session.commit()
    except IntegrityError:
        # Likely concurrent seed. Safe to ignore.
        await session.rollback()
        return
    except SQLAlchemyError:
        await session.rollback()
        logger.exception("Failed to seed system catalog")
        raise
