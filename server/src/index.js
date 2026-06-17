/**
 * Express Server Entry Point
 *
 * Configures middleware, mounts API routes, and starts the HTTP server.
 */

require("dotenv").config();
const express = require("express");
const cors = require("cors");
const pool = require("./db/pool");
const usersRouter = require("./routes/users");

const app = express();
const PORT = process.env.PORT || 5000;

// ──────────────────────────────────────
// Middleware
// ──────────────────────────────────────
app.use(cors({
  origin: ["http://localhost:3000", "http://localhost:3001"],
  credentials: true,
}));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// ──────────────────────────────────────
// API Routes
// ──────────────────────────────────────
app.use("/api/users", usersRouter);

// Health check endpoint
app.get("/api/health", async (req, res) => {
  try {
    const result = await pool.query("SELECT NOW()");
    res.json({
      status: "healthy",
      timestamp: result.rows[0].now,
      database: "connected",
    });
  } catch (err) {
    res.status(503).json({
      status: "unhealthy",
      database: "disconnected",
      error: err.message,
    });
  }
});

// ──────────────────────────────────────
// 404 Handler
// ──────────────────────────────────────
app.use((req, res) => {
  res.status(404).json({
    success: false,
    error: `Route ${req.method} ${req.url} not found`,
  });
});

// ──────────────────────────────────────
// Global Error Handler
// ──────────────────────────────────────
app.use((err, req, res, _next) => {
  console.error("Unhandled error:", err);
  res.status(500).json({
    success: false,
    error: process.env.NODE_ENV === "production"
      ? "Internal server error"
      : err.message,
  });
});

// ──────────────────────────────────────
// Start Server
// ──────────────────────────────────────
app.listen(PORT, () => {
  console.log(`
  🚀 Server running on http://localhost:${PORT}
  📡 API endpoint: http://localhost:${PORT}/api/users
  💚 Health check: http://localhost:${PORT}/api/health
  `);
});
