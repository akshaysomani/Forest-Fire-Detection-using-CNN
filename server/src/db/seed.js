/**
 * Database Seed Script
 *
 * Creates the `users` table if it doesn't exist and inserts sample data.
 * Run with: npm run db:seed
 */

const pool = require("./pool");

async function seed() {
  const client = await pool.connect();

  try {
    await client.query("BEGIN");

    // Create the users table
    await client.query(`
      CREATE TABLE IF NOT EXISTS users (
        id         SERIAL PRIMARY KEY,
        name       VARCHAR(100) NOT NULL,
        email      VARCHAR(255) UNIQUE NOT NULL,
        role       VARCHAR(50) DEFAULT 'viewer',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
      );
    `);
    console.log("✅ users table created (or already exists)");

    // Insert sample users (skip if they already exist)
    const sampleUsers = [
      { name: "Akshay Somani", email: "akshay@forestfire.org", role: "admin" },
      { name: "Priya Sharma",  email: "priya@forestfire.org",  role: "analyst" },
      { name: "Rahul Gupta",   email: "rahul@forestfire.org",  role: "viewer" },
    ];

    for (const user of sampleUsers) {
      await client.query(
        `INSERT INTO users (name, email, role)
         VALUES ($1, $2, $3)
         ON CONFLICT (email) DO NOTHING`,
        [user.name, user.email, user.role]
      );
    }
    console.log("✅ Sample users seeded");

    await client.query("COMMIT");
  } catch (err) {
    await client.query("ROLLBACK");
    console.error("❌ Seeding failed:", err.message);
    throw err;
  } finally {
    client.release();
    await pool.end();
  }
}

seed()
  .then(() => {
    console.log("🌱 Database seeding complete!");
    process.exit(0);
  })
  .catch(() => {
    process.exit(1);
  });
