import tempfile
import os

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import schemas
from .feature_extraction import extract_au_vector
from .scoring import build_baseline_profile, score_against_baseline
from .session_store import create_session, get_session

app = FastAPI(title="Facial Deviation Lie-Potential API")

# Dev CORS -- open for local React dev server. Lock this down to your actual
# frontend origin before deploying anywhere real.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

RECOMMENDED_MIN_BASELINE_SAMPLES = 3


async def _save_upload_to_temp(upload: UploadFile) -> str:
    suffix = os.path.splitext(upload.filename or "")[1] or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await upload.read())
        return tmp.name


@app.post("/session", response_model=schemas.SessionCreatedResponse)
def start_session():
    session = create_session()
    return schemas.SessionCreatedResponse(session_id=session.session_id)


@app.post(
    "/session/{session_id}/baseline",
    response_model=schemas.BaselineSampleResponse,
)
async def add_baseline_sample(session_id: str, clip: UploadFile = File(...)):
    try:
        session = get_session(session_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    temp_path = await _save_upload_to_temp(clip)
    try:
        au_vector = extract_au_vector(temp_path)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        os.remove(temp_path)

    session.baseline_vectors.append(au_vector)
    n = len(session.baseline_vectors)
    return schemas.BaselineSampleResponse(
        session_id=session_id,
        samples_collected=n,
        ready_to_finalize=n >= RECOMMENDED_MIN_BASELINE_SAMPLES,
    )


@app.post(
    "/session/{session_id}/baseline/finalize",
    response_model=schemas.BaselineFinalizedResponse,
)
def finalize_baseline(session_id: str):
    try:
        session = get_session(session_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if not session.baseline_vectors:
        raise HTTPException(status_code=400, detail="No baseline samples collected yet.")

    session.baseline_profile = build_baseline_profile(session.baseline_vectors)
    warnings = session.baseline_profile.flag_low_confidence_inputs(
        min_samples=RECOMMENDED_MIN_BASELINE_SAMPLES
    )
    return schemas.BaselineFinalizedResponse(
        session_id=session_id,
        n_samples=session.baseline_profile.n_samples,
        warnings=warnings,
    )


@app.post(
    "/session/{session_id}/question",
    response_model=schemas.QuestionResultResponse,
)
async def score_question(
    session_id: str, question_id: str, clip: UploadFile = File(...)
):
    try:
        session = get_session(session_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if session.baseline_profile is None:
        raise HTTPException(
            status_code=400,
            detail="Baseline not finalized yet -- call /baseline/finalize first.",
        )

    temp_path = await _save_upload_to_temp(clip)
    try:
        au_vector = extract_au_vector(temp_path)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        os.remove(temp_path)

    result = score_against_baseline(au_vector, session.baseline_profile)
    response = schemas.QuestionResultResponse(
        session_id=session_id,
        question_id=question_id,
        meter=result["meter"],
        bucket=result["bucket"],
        warnings=result["warnings"],
    )
    session.results.append(response.model_dump())
    return response


@app.get("/session/{session_id}", response_model=schemas.SessionSummaryResponse)
def session_summary(session_id: str):
    try:
        session = get_session(session_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return schemas.SessionSummaryResponse(
        session_id=session_id,
        n_baseline_samples=len(session.baseline_vectors),
        results=[schemas.QuestionResultResponse(**r) for r in session.results],
    )
