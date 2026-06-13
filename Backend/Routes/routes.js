const router = require("express").Router();
const mongoose = require("mongoose");
const passport = require("../config/passport");
const { signup, login, refresh } = require("../Controller/AuthController");
const { oauthSuccess, FRONTEND_URL } = require("../Controller/OAuthController");

function sendOAuthNotConfigured(res, title, detail) {
  return res
    .status(503)
    .type("html")
    .send(
      `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${title}</title></head><body style="font-family:system-ui;max-width:36rem;margin:2rem auto;padding:0 1rem"><h1>${title}</h1><p>${detail}</p><p>Restart the server after editing <code>.env</code>.</p></body></html>`
    );
}

router.post("/signup", signup);
router.post("/login", login);
router.post("/refresh", refresh);

/** OAuth callbacks load/create users in MongoDB. If DB is down, Mongoose buffers forever → blank browser. */
function requireMongoForOAuth(req, res, next) {
  if (mongoose.connection.readyState === 1) return next();
  return res.redirect(`${FRONTEND_URL}/auth/callback?error=db`);
}

function googleConfigured(req, res, next) {
  if (!process.env.GOOGLE_CLIENT_ID || !process.env.GOOGLE_CLIENT_SECRET) {
    return sendOAuthNotConfigured(
      res,
      "Google sign-in not configured",
      "Add <code>GOOGLE_CLIENT_ID</code> and <code>GOOGLE_CLIENT_SECRET</code> to your backend <code>.env</code> file."
    );
  }
  next();
}

function githubConfigured(req, res, next) {
  if (!process.env.GITHUB_CLIENT_ID || !process.env.GITHUB_CLIENT_SECRET) {
    return sendOAuthNotConfigured(
      res,
      "GitHub sign-in not configured",
      "Add <code>GITHUB_CLIENT_ID</code> and <code>GITHUB_CLIENT_SECRET</code> to your backend <code>.env</code> file."
    );
  }
  next();
}

router.get("/google", googleConfigured, passport.authenticate("google", { scope: ["profile", "email"] }));

router.get(
  "/google/callback",
  requireMongoForOAuth,
  googleConfigured,
  passport.authenticate("google", {
    failureRedirect: `${FRONTEND_URL}/auth/callback?error=google`,
  }),
  oauthSuccess
);

router.get("/github", githubConfigured, passport.authenticate("github", { scope: ["user:email"] }));

router.get(
  "/github/callback",
  requireMongoForOAuth,
  githubConfigured,
  passport.authenticate("github", {
    failureRedirect: `${FRONTEND_URL}/auth/callback?error=github`,
  }),
  oauthSuccess
);

module.exports = router;
