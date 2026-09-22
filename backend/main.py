from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uuid


app = FastAPI(title="AI Lie Detection Backend")


# --------------------------------------------------
# CORS
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# Temporary in-memory sessions
# --------------------------------------------------

sessions = {}


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "AI Lie Detection Backend is running"
    }


# --------------------------------------------------
# CREATE SESSION
# --------------------------------------------------

@app.post("/session")
def create_session():

    session_id = str(uuid.uuid4())

    sessions[session_id] = {
        "baseline_samples": 0,
        "baseline_finalized": False,
        "questions": {}
    }

    return {
        "session_id": session_id
    }


# --------------------------------------------------
# UPLOAD BASELINE CLIP
# --------------------------------------------------

@app.post("/session/{session_id}/baseline")
async def upload_baseline(
    session_id: str,
    clip: UploadFile = File(...)
):

    if session_id not in sessions:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    # Read the uploaded video
    video_data = await clip.read()

    # Temporary behavior:
    # We are just confirming that the video reached the backend.
    # Actual facial analysis will be added later.

    if len(video_data) == 0:
        raise HTTPException(
            status_code=400,
            detail="Empty video file"
        )

    # Temporary sample count
    sessions[session_id]["baseline_samples"] += 1

    return {
        "samples_collected": sessions[session_id]["baseline_samples"],
        "ready_to_finalize": True
    }


# --------------------------------------------------
# FINALIZE BASELINE
# --------------------------------------------------

@app.post("/session/{session_id}/baseline/finalize")
def finalize_baseline(session_id: str):

    if session_id not in sessions:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    session = sessions[session_id]

    if session["baseline_samples"] == 0:
        raise HTTPException(
            status_code=400,
            detail="No baseline samples uploaded"
        )

    session["baseline_finalized"] = True

    return {
        "n_samples": session["baseline_samples"],
        "warnings": []
    }


# --------------------------------------------------
# SCORE QUESTION
# --------------------------------------------------

@app.post("/session/{session_id}/question")
async def score_question(
    session_id: str,
    question_id: str,
    clip: UploadFile = File(...)
):

    if session_id not in sessions:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    session = sessions[session_id]

    if not session["baseline_finalized"]:
        raise HTTPException(
            status_code=400,
            detail="Baseline has not been finalized"
        )

    video_data = await clip.read()

    if len(video_data) == 0:
        raise HTTPException(
            status_code=400,
            detail="Empty video file"
        )

    # --------------------------------------------------
    # TEMPORARY RESULT
    # --------------------------------------------------
    #
    # Actual facial-expression / ML analysis
    # will be added here later.
    #

    result = {
        "meter": 50,
        "bucket": "uncertain",
        "warnings": []
    }

    session["questions"][question_id] = result

    return result