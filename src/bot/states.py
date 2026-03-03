from aiogram.fsm.state import State, StatesGroup


class CreateWorkout(StatesGroup):
    waiting_title = State()


class WorkoutMenu(StatesGroup):
    active_workout = State()


class AddExercise(StatesGroup):
    waiting_muscle_group = State()
    waiting_exercise = State()
    waiting_comment_optional = State()
    waiting_custom_group_name = State()
    waiting_custom_group_rename = State()
    waiting_custom_exercise_name = State()
    waiting_custom_exercise_rename = State()


class AddSet(StatesGroup):
    waiting_weight = State()
    waiting_reps = State()


class FinishWorkout(StatesGroup):
    waiting_comment_optional = State()


class EditMuscleGroup(StatesGroup):
    waiting_name = State()


class EditExerciseName(StatesGroup):
    waiting_name = State()


class EditWorkoutExercise(StatesGroup):
    waiting_comment = State()
    waiting_set_weight = State()
    waiting_set_reps = State()
