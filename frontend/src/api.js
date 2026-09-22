const BASE_URL = "http://localhost:8000";

export async function createSession() {
  const res = await fetch(`${BASE_URL}/session`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to create session");
  return res.json(); // { session_id }
}

export async function uploadBaselineClip(sessionId, blob) {
  const form = new FormData();
  form.append("clip", blob, "baseline.webm");
  const res = await fetch(`${BASE_URL}/session/${sessionId}/baseline`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error((await res.json()).detail || "Baseline upload failed");
  return res.json(); // { samples_collected, ready_to_finalize }
}

export async function finalizeBaseline(sessionId) {
  const res = await fetch(`${BASE_URL}/session/${sessionId}/baseline/finalize`, {
    method: "POST",
  });
  if (!res.ok) throw new Error((await res.json()).detail || "Finalize failed");
  return res.json(); // { n_samples, warnings }
}

export async function scoreQuestion(sessionId, questionId, blob) {
  const form = new FormData();
  form.append("clip", blob, "question.webm");
  const res = await fetch(
    `${BASE_URL}/session/${sessionId}/question?question_id=${encodeURIComponent(questionId)}`,
    { method: "POST", body: form }
  );
  if (!res.ok) throw new Error((await res.json()).detail || "Scoring failed");
  return res.json(); // { meter, bucket, warnings }
}
