const router = require("express").Router();

async function parseMlResponse(response) {
  const text = await response.text();
  try {
    return JSON.parse(text);
  } catch (_err) {
    return { detail: text || "ML service returned invalid JSON." };
  }
}

const ML_BASE = () => process.env.ML_API_URL || "http://localhost:8000/api/v1";

// POST /api/v1/analyze — start analysis (proxied to ML)
router.post("/analyze", async (req, res) => {
  try {
    const response = await fetch(`${ML_BASE()}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),
    });
    const data = await parseMlResponse(response);
    return res.status(response.status).json(data);
  } catch (error) {
    console.error("Error proxying POST /analyze to ML:", error);
    return res.status(502).json({ detail: "Failed to connect to ML service" });
  }
});

// GET /api/v1/analyze/:task_id — poll status (proxied to ML)
router.get("/analyze/:task_id", async (req, res) => {
  try {
    const response = await fetch(`${ML_BASE()}/analyze/${req.params.task_id}`);
    const data = await parseMlResponse(response);
    return res.status(response.status).json(data);
  } catch (error) {
    console.error("Error proxying GET /analyze/:id to ML:", error);
    return res.status(502).json({ detail: "Failed to connect to ML service" });
  }
});

module.exports = router;
