const passport = require("passport");
const GoogleStrategy = require("passport-google-oauth20").Strategy;
const GitHubStrategy = require("passport-github2").Strategy;
const User = require("../Models/User");
const { upsertOAuthUser, fetchPrimaryGitHubEmail } = require("../services/oauthUser");

passport.serializeUser((user, done) => {
  done(null, user._id.toString());
});

passport.deserializeUser(async (id, done) => {
  try {
    const user = await User.findById(id);
    done(null, user);
  } catch (err) {
    done(err);
  }
});

if (process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET) {
  passport.use(
    new GoogleStrategy(
      {
        clientID: process.env.GOOGLE_CLIENT_ID,
        clientSecret: process.env.GOOGLE_CLIENT_SECRET,
        callbackURL: process.env.GOOGLE_CALLBACK_URL || "http://localhost:5000/api/auth/google/callback",
      },
      async (accessToken, refreshToken, profile, done) => {
        try {
          const email = profile.emails?.[0]?.value ?? null;
          const name = profile.displayName || profile.name?.givenName || "User";
          const user = await upsertOAuthUser({
            provider: "google",
            profileId: profile.id,
            email,
            name,
          });
          done(null, user);
        } catch (err) {
          done(err);
        }
      }
    )
  );
}

if (process.env.GITHUB_CLIENT_ID && process.env.GITHUB_CLIENT_SECRET) {
  passport.use(
    new GitHubStrategy(
      {
        clientID: process.env.GITHUB_CLIENT_ID,
        clientSecret: process.env.GITHUB_CLIENT_SECRET,
        callbackURL: process.env.GITHUB_CALLBACK_URL || "http://localhost:5000/api/auth/github/callback",
      },
      async (accessToken, refreshToken, profile, done) => {
        try {
          let email =
            profile.emails?.find((e) => e.primary)?.value ||
            profile.emails?.[0]?.value ||
            null;
          if (!email) {
            email = await fetchPrimaryGitHubEmail(accessToken);
          }
          const name = profile.displayName || profile.username || "User";
          const user = await upsertOAuthUser({
            provider: "github",
            profileId: String(profile.id),
            email,
            name,
          });
          done(null, user);
        } catch (err) {
          done(err);
        }
      }
    )
  );
}

module.exports = passport;
