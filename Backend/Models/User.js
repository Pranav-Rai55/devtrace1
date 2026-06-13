const mongoose = require("mongoose");

const userSchema = new mongoose.Schema(
  {
    name:{
        type:String,
        required:true,
    },
    email: {
      type: String,
      required: true,
      unique: true,
      lowercase: true,
      trim: true,
    },
    googleId: {
      type: String,
      sparse: true,
      unique: true,
    },
    githubId: {
      type: String,
      sparse: true,
      unique: true,
    },
    passwordHash: {
      type: String,
      required: function requiredPassword() {
        return !this.googleId && !this.githubId;
      },
      select: false, // important: do not return hash by default
    },
    roles: {
      type: [String],
      default: ["user"],
    },
  },
  { timestamps: true }
);

module.exports = mongoose.model("User", userSchema);