const { signAccessToken, signRefreshToken } = require("../Token/Token");
const { setRefreshCookie } = require("./AuthController");

const FRONTEND_URL = process.env.FRONTEND_URL || "http://localhost:5173";

function oauthSuccess(req, res, next) {
  const user = req.user;
  if (!user) {
    return res.redirect(`${FRONTEND_URL}/auth/callback?error=oauth_failed`);
  }

  const accessToken = signAccessToken(user);
  const refreshToken = signRefreshToken(user);
  setRefreshCookie(res, refreshToken);

  const token = encodeURIComponent(accessToken);
  const target = `${FRONTEND_URL}/auth/callback#access_token=${token}`;

  req.logout((err) => {
    if (err) return next(err);
    res.redirect(target);
  });
}

module.exports = { oauthSuccess, FRONTEND_URL };
