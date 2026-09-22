from pydantic import BaseModel


class SessionCreatedResponse(BaseModel):
    session_id: str


class BaselineSampleResponse(BaseModel):
    session_id: str
    samples_collected: int
    ready_to_finalize: bool  # true once samples_collected >= recommended minimum


class BaselineFinalizedResponse(BaseModel):
    session_id: str
    n_samples: int
    warnings: list[str]


class QuestionResultResponse(BaseModel):
    session_id: str
    question_id: str
    meter: float          # 0-100, for the UI's confidence/lie-potential meter
    bucket: str            # "Low" | "Medium" | "High"
    warnings: list[str]


class SessionSummaryResponse(BaseModel):
    session_id: str
    n_baseline_samples: int
    results: list[QuestionResultResponse]
