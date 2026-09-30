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
    deception_probability: float  # 0.0 to 1.0 (ML model probability)
    baseline_deviation: float     # 0.0 to 1.0 (Personal baseline deviation)
    risk_score: float             # 0.0 to 100.0 (Combined deception risk score)
    risk_level: str               # "Low" | "Medium" | "High"
    meter: float                  # 0.0 to 100.0 (UI score representation)
    bucket: str                   # "Low" | "Medium" | "High" (UI category)
    warnings: list[str]
    disclaimer: str               # Explanatory risk disclaimer


class SessionSummaryResponse(BaseModel):
    session_id: str
    n_baseline_samples: int
    results: list[QuestionResultResponse]
