const User = require("../Models/User");

async function fetchPrimaryGitHubEmail(accessToken) {
  const res = await fetch("https://api.github.com/user/emails", {
    headers: {
      Authorization: `Bearer ${accessToken}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
    },
  });
  if (!res.ok) return null;
  const data = await res.json();
  const primary = data.find((e) => e.primary)?.email;
  const verified = data.find((e) => e.verified)?.email;
  return primary || verified || data[0]?.email || null;
}

/**
 * @param {object} opts
 * @param {'google'|'github'} opts.provider
 * @param {string} opts.profileId
 * @param {string|null} opts.email
 * @param {string} opts.name
 */
async function upsertOAuthUser({ provider, profileId, email, name }) {
  const idField = provider === "google" ? "googleId" : "githubId";

  let user = await User.findOne({ [idField]: profileId });
  if (user) return user;

  if (email) {
    const normalized = email.toLowerCase().trim();
    user = await User.findOne({ email: normalized });
    if (user) {
      if (user[idField]) {
        const err = new Error("This email is already linked to another account.");
        err.code = "OAUTH_LINK_CONFLICT";
        throw err;
      }
      user[idField] = profileId;
      if (!user.name) user.name = name;
      await user.save();
      return user;
    }

    return User.create({
      name: name || "User",
      email: normalized,
      [idField]: profileId,
      roles: ["user"],
    });
  }

  const err = new Error("Your GitHub account must expose a verified email (enable user:email or add a public email).");
  err.code = "OAUTH_NO_EMAIL";
  throw err;
}

module.exports = { upsertOAuthUser, fetchPrimaryGitHubEmail };
