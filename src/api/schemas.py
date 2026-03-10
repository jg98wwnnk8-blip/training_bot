from pydantic import BaseModel


class WebAppAuthRequest(BaseModel):
    initData: str


class WebAppAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: int


class SetResponse(BaseModel):
    set_number: int
    weight: float
    reps: int


class WorkoutExerciseResponse(BaseModel):
    workout_exercise_id: int
    exercise_id: int
    exercise_name: str
    comment: str | None
    sets: list[SetResponse]


class WorkoutListItemResponse(BaseModel):
    id: int
    title: str
    date_utc: str
    comment: str | None
    exercise_count: int
    total_volume: float


class WorkoutListResponse(BaseModel):
    items: list[WorkoutListItemResponse]
    total: int
    limit: int
    offset: int


class WorkoutDetailResponse(BaseModel):
    id: int
    title: str
    date_utc: str
    comment: str | None
    status: str
    exercises: list[WorkoutExerciseResponse]


class SearchResponse(BaseModel):
    items: list[WorkoutListItemResponse]
    total: int


class MuscleGroupFilterItem(BaseModel):
    id: int
    name: str
    emoji: str


class ExerciseFilterItem(BaseModel):
    id: int
    muscle_group_id: int
    name: str


class FiltersResponse(BaseModel):
    muscle_groups: list[MuscleGroupFilterItem]
    exercises: list[ExerciseFilterItem]
