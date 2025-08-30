// Helper: get token from localStorage
function getToken() {
    return localStorage.getItem("token");
}

// -------------------
// REGISTER
// -------------------
async function register(username, password) {
    const res = await fetch("/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
    });
    return await res.json();
}

// -------------------
// LOGIN
// -------------------
async function login(username, password) {
    const res = await fetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
    });
    const data = await res.json();
    if (res.ok) {
        localStorage.setItem("token", data.access_token);
        localStorage.setItem("username", data.username);
        localStorage.setItem("role", data.role);
        localStorage.setItem("points", data.points);
    }
    return data;
}

// -------------------
// GET CHALLENGES
// -------------------
async function getChallenges() {
    const res = await fetch("/challenges", {
        headers: { Authorization: "Bearer " + getToken() },
    });
    return await res.json();
}

// -------------------
// SUBMIT CHALLENGE
// -------------------
async function submitChallenge(challenge_id, proof_text) {
    const res = await fetch("/submissions", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: "Bearer " + getToken(),
        },
        body: JSON.stringify({ challenge_id, proof_text }),
    });
    return await res.json();
}

// -------------------
// LEADERBOARD
// -------------------
async function getLeaderboard() {
    const res = await fetch("/leaderboard", {
        headers: { Authorization: "Bearer " + getToken() },
    });
    return await res.json();
}

// Example usage:
// login("admin","admin123").then(console.log)
// getChallenges().then(console.log)
