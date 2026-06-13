const bcrypt = require("bcryptjs");
const User = require("../Models/User");
const { signAccessToken, signRefreshToken, verifyRefreshToken } = require("../Token/Token");

const isProd = process.env.NODE_ENV === "production";

function setRefreshCookie(res, refreshToken) {
  res.cookie("refreshToken", refreshToken, {
    httpOnly: true,
    secure: isProd,         // true only in https production
    sameSite: "strict",     // if frontend different domain, use "none" + secure true
    path: "/api/auth/refresh",
    maxAge: 30 * 24 * 60 * 60 * 1000, // 30 days
  });
}

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function isStrongPassword(pw) {
  // simple strength check: 8+ length
  return typeof pw === "string" && pw.length >= 8;
}

// ✅ SIGNUP
async function signup(req, res) {
  const { email, password, name: bodyName } = req.body || {};

  if (!email || !password) {
    return res.status(400).json({ message: "Email and password are required" });
  }
  const name = (bodyName && String(bodyName).trim()) || email.split("@")[0];
  if (!isValidEmail(email)) {
    return res.status(400).json({ message: "Invalid email format" });
  }
  if (!isStrongPassword(password)) {
    return res.status(400).json({ message: "Password must be at least 8 characters" });
  }

  const existing = await User.findOne({ email: email.toLowerCase() });
  if (existing) {
    return res.status(409).json({ message: "Email already registered" });
  }

  const passwordHash = await bcrypt.hash(password, 12);
  const user = await User.create({
    name,
    email: email.toLowerCase(),
    passwordHash,
    roles: ["user"],
  });

  // Auto-login after signup (common UX)
  const accessToken = signAccessToken(user);
  const refreshToken = signRefreshToken(user);

  setRefreshCookie(res, refreshToken);

  return res.status(201).json({
    message: "Signup successful",
    user: { id: user._id, email: user.email, roles: user.roles },
    accessToken,
  });
}

// ✅ LOGIN
async function login(req, res) {
  const { email, password } = req.body || {};

  if (!email || !password) {
    return res.status(400).json({ message: "Email and password are required" });
  }

  // Need passwordHash => select("+passwordHash")
  const user = await User.findOne({ email: email.toLowerCase() }).select("+passwordHash");
  if (!user) {
    return res.status(401).json({ message: "Invalid credentials" });
  }

  if (!user.passwordHash) {
    return res.status(401).json({
      message: "This account uses Google or GitHub sign-in. Use that provider to log in.",
    });
  }

  const ok = await bcrypt.compare(password, user.passwordHash);
  if (!ok) {
    return res.status(401).json({ message: "Invalid credentials" });
  }

  const accessToken = signAccessToken(user);
  const refreshToken = signRefreshToken(user);

  setRefreshCookie(res, refreshToken);

  return res.json({
    message: "Login successful",
    user: { id: user._id, email: user.email, roles: user.roles },
    accessToken,
  });
}

// ✅ REFRESH ACCESS TOKEN
async function refresh(req, res) {
  const { refreshToken } = req.cookies;

  if (!refreshToken) {
    return res.status(401).json({ message: "Refresh token required" });
  }

  const payload = verifyRefreshToken(refreshToken);
  if (!payload) {
    return res.status(401).json({ message: "Invalid refresh token" });
  }

  const user = await User.findById(payload.sub);
  if (!user) {
    return res.status(401).json({ message: "User not found" });
  }

  const newAccessToken = signAccessToken(user);

  return res.json({
    message: "Token refreshed",
    accessToken: newAccessToken,
  });
}

module.exports = { signup, login, refresh, setRefreshCookie };