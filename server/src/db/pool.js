/**
 * PostgreSQL Connection Pool Configuration
 *
 * Uses the `pg` library to create a reusable connection pool.
 * All database credentials are loaded from environment variables.
 */

const { Pool } = require("pg");
require("dotenv").config();

const pool = new Pool({
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  host: process.env.DB_HOST,
  port: parseInt(process.env.DB_PORT, 10) || 5432,
  database: process.env.DB_NAME,

  // SSL configuration (required for Supabase)
  ssl: process.env.DB_SSL === "true" ? { rejectUnauthorized: false } : false,

  // Pool configuration
  max: 20,                    // Maximum number of clients in the pool
  idleTimeoutMillis: 30000,   // Close idle clients after 30 seconds
  connectionTimeoutMillis: 10000, // Fail if connection takes longer than 10 seconds
});

// Log successful connection on first query
pool.on("connect", () => {
  console.log("📦 New client connected to PostgreSQL");
});

// Log pool errors
pool.on("error", (err) => {
  console.error("❌ Unexpected error on idle PostgreSQL client:", err.message);
  process.exit(-1);
});

module.exports = pool;
