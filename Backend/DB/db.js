const mongoose = require("mongoose");

const connectDB = async () => {
  const uri = process.env.DB_URI || process.env.MONGO_URI;
  if (!uri) {
    console.warn("[DB] DB_URI (or MONGO_URI) is missing from .env — running in DB-less mode");
    return;
  }
  try {
    await mongoose.connect(uri, { serverSelectionTimeoutMS: 5000 });
    console.log("[DB] ✅ MongoDB connected");
  } catch (error) {
    console.warn("[DB] ⚠️  Connection failed (non-fatal in dev):", error.message);
    if (process.env.NODE_ENV === "production") {
      throw error;
    }
  }
};

module.exports = connectDB;
