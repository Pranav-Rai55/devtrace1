const path = require("path");
require("dotenv").config({ path: path.join(__dirname, ".env") });

const express = require("express");
const cookieParser = require("cookie-parser");
const session = require("express-session");
const cors = require("cors");
const passport = require("./config/passport");
const authRoutes = require("./Routes/routes");
const analysisRoutes = require("./Routes/analysis");
const connectDB = require("./DB/db");

const PORT = process.env.PORT || 5000;
const isProd = process.env.NODE_ENV === "production";
const FRONTEND_URL = process.env.FRONTEND_URL || "http://localhost:5173";
const FRONTEND_URL_ALT = process.env.FRONTEND_URL_ALT || "http://localhost:5174";
const FRONTEND_URL_ALT2 = process.env.FRONTEND_URL_ALT2 || "http://localhost:5175";
const allowedOrigins = [FRONTEND_URL, FRONTEND_URL_ALT, FRONTEND_URL_ALT2];

const app = express();

app.use(
  cors({
    origin: isProd
      ? (origin, callback) => {
          if (!origin || allowedOrigins.includes(origin)) {
            callback(null, true);
          } else {
            callback(new Error(`Origin ${origin} not allowed by CORS`));
          }
        }
      : (origin, callback) => {
          if (!origin || /^https?:\/\/localhost(:\d+)?$/.test(origin)) {
            callback(null, true);
          } else {
            callback(new Error(`Origin ${origin} not allowed by CORS`));
          }
        },
    credentials: true,
  })
);

app.use(express.json());
app.use(cookieParser());
app.use(
  session({
    secret: process.env.SESSION_SECRET || "dev-session-secret-change-me",
    resave: false,
    saveUninitialized: false,
    cookie: {
      secure: isProd,
      httpOnly: true,
      sameSite: isProd ? "none" : "lax",
      maxAge: 10 * 60 * 1000,
    },
  })
);

app.use(passport.initialize());
app.use(passport.session());

connectDB();

app.post("/api/v1/healthcheck", (req, res) => {
  res.json({ ok: true, route: "/api/v1/healthcheck" });
});

app.use("/api/v1", analysisRoutes);
app.use("/api/auth", authRoutes);

app.get("/", (req, res) => res.send("DevTrace backend running ✅"));

app.use((err, req, res, next) => {
  console.error(err);
  if (req.originalUrl && String(req.originalUrl).includes("/callback")) {
    const q = err.code === "OAUTH_NO_EMAIL" ? "no_email" : "server";
    return res.redirect(`${FRONTEND_URL}/auth/callback?error=${q}`);
  }
  if (res.headersSent) return next(err);
  res.status(500).json({ message: "Server error" });
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
