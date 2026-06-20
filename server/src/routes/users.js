/**
 * Users API Routes
 *
 * GET /api/users       - Fetch all users
 * GET /api/users/:id   - Fetch a single user by ID
 */

const express = require("express");
const pool = require("../db/pool");

const router = express.Router();

/**
 * GET /api/users
 * Returns all users from the database, ordered by creation date.
 */
router.get("/", async (req, res) => {
  try {
    const result = await pool.query(
      "SELECT id, name, email, role, created_at FROM node_users ORDER BY created_at DESC"
    );
    res.json({
      success: true,
      count: result.rows.length,
      data: result.rows,
    });
  } catch (err) {
    console.error("Error fetching users:", err.message);
    res.status(500).json({
      success: false,
      error: "Failed to fetch users from the database",
    });
  }
});

/**
 * GET /api/users/:id
 * Returns a single user by their ID.
 */
router.get("/:id", async (req, res) => {
  const { id } = req.params;

  try {
    const result = await pool.query(
      "SELECT id, name, email, role, created_at FROM node_users WHERE id = $1",
      [id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({
        success: false,
        error: `User with ID ${id} not found`,
      });
    }

    res.json({
      success: true,
      data: result.rows[0],
    });
  } catch (err) {
    console.error("Error fetching user:", err.message);
    res.status(500).json({
      success: false,
      error: "Failed to fetch user from the database",
    });
  }
});

module.exports = router;
