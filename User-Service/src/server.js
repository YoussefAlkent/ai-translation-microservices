const express = require('express');
const cors = require('cors');
const supertokens = require('supertokens-node');
const Session = require('supertokens-node/recipe/session');
const EmailPassword = require('supertokens-node/recipe/emailpassword');
const { verifySession } = require('supertokens-node/recipe/session/framework/express');
const { Pool } = require('pg');

const app = express();
const port = 3001;

app.use(express.json());

const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
});

supertokens.init({
    framework: "express",
    supertokens: {
        connectionURI: "http://supertokens:3567",
        apiKey: process.env.SUPERTOKENS_API_KEY
    },
    appInfo: {
        appName: "Cloud Project",
        apiDomain: "http://localhost:8000",
        websiteDomain: "http://localhost:4200"
    },
    recipeList: [
        EmailPassword.init(),
        Session.init()
    ]
});

app.use(cors({
    origin: "http://localhost:4200",
    credentials: true,
}));

app.get('/health', (_, res) => {
    res.json({ status: 'healthy' });
});

// Add authentication endpoints
app.post('/auth/signup', async (req, res) => {
    let { formFields } = req.body;
    try {
        await EmailPassword.signUp('public', formFields.email, formFields.password);
        const user = await EmailPassword.signIn('public', formFields.email, formFields.password);
        
        // Create user profile
        await pool.query(
            'INSERT INTO user_profiles (user_id, email) VALUES ($1, $2)',
            [user.user.id, formFields.email]
        );
        
        res.json({ status: 'success', userId: user.user.id });
    } catch (err) {
        res.status(400).json({ status: 'error', message: err.message });
    }
});

app.post('/auth/signin', async (req, res) => {
    let { formFields } = req.body;
    try {
        const user = await EmailPassword.signIn('public', formFields.email, formFields.password);
        res.json({ status: 'success', userId: user.user.id });
    } catch (err) {
        res.status(400).json({ status: 'error', message: err.message });
    }
});

app.post('/api/users/profile', verifySession(), async (req, res) => {
    const userId = req.session.getUserId();
    const { name } = req.body;

    try {
        await pool.query(
            'INSERT INTO user_profiles (user_id, email, name) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO UPDATE SET name = $3',
            [userId, req.session.getEmail(), name]
        );
        res.json({ success: true });
    } catch (err) {
        res.status(500).json({ error: 'Failed to update profile' });
    }
});

app.get('/api/users/profile', verifySession(), async (req, res) => {
    const userId = req.session.getUserId();

    try {
        const result = await pool.query('SELECT * FROM user_profiles WHERE user_id = $1', [userId]);
        res.json(result.rows[0] || {});
    } catch (err) {
        res.status(500).json({ error: 'Failed to fetch profile' });
    }
});

// Add connection retry logic
const connectWithRetry = async () => {
    const maxRetries = 5;
    let currentTry = 1;

    while (currentTry <= maxRetries) {
        try {
            await pool.connect();
            console.log('Connected to PostgreSQL');
            return;
        } catch (err) {
            console.log(`Failed to connect to PostgreSQL (attempt ${currentTry}/${maxRetries}):`, err.message);
            await new Promise(resolve => setTimeout(resolve, 5000)); // Wait 5 seconds
            currentTry++;
        }
    }
    throw new Error('Failed to connect to PostgreSQL after multiple retries');
};

// Initialize the application
const initializeApp = async () => {
    try {
        await connectWithRetry();
        
        app.listen(port, () => {
            console.log(`User-Service listening at http://localhost:${port}`);
        });
    } catch (err) {
        console.error('Failed to initialize application:', err);
        process.exit(1);
    }
};

initializeApp();
