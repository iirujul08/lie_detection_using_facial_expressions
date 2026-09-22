# Facial deviation lie-potential demo

Architecture: React frontend -> FastAPI backend (py-feat AU extraction + deviation
scoring in-process) -> returns a score -> React renders a meter.

Reminder of the framing this code assumes (from the design discussion): the score
is "deviation from this person's own calibrated baseline," not a verified lie
detector. Baseline questions are low-stakes/unfakeable-by-design, and multiple
baseline samples are averaged so one odd sample doesn't corrupt the reference.

## Backend

```
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

First request will be slow -- py-feat downloads model weights on first use.

## Frontend

```
cd frontend
npm install
npm run dev
```

Open the printed localhost URL. Browser will ask for webcam permission.

## What's stubbed / not done yet

- `scoring.py`: `AU_WEIGHTS` is uniform (placeholder). Train a model on labeled
  deceptive/truthful clips to learn actual per-AU importance weights, then load
  them here instead of the uniform vector.
- `scoring.py`: the 0.15/0.35 distance thresholds for Low/Medium/High are
  placeholders -- calibrate against real session data once you have some.
- `session_store.py`: in-memory, single-process. Fine for a demo/viva; swap for a
  real DB before this needs to survive a restart or handle concurrent users.
- No auth -- add before this is anything but a local demo.
