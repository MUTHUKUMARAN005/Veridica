const storageKey = 'veridica.frontend-auth.v1';
let accessToken = null;
let currentUser = null;
function loadAuthFromStorage() {
    try {
        const stored = localStorage.getItem(storageKey);
        if (stored) {
            const parsed = JSON.parse(stored);
            accessToken = parsed.accessToken ?? null;
            currentUser = parsed.currentUser ?? null;
        }
    }
    catch {
        accessToken = null;
        currentUser = null;
    }
}
function saveAuthToStorage() {
    try {
        localStorage.setItem(storageKey, JSON.stringify({ accessToken, currentUser }));
    }
    catch {
        // Storage full or unavailable - silently ignore
    }
}
loadAuthFromStorage();
async function request(path, body) {
    const response = await fetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
        const detail = typeof payload === 'object' && payload !== null && 'detail' in payload
            ? String(payload.detail)
            : 'The authentication request failed.';
        throw new Error(detail);
    }
    return payload;
}
export function register(email, password) {
    return request('/api/v1/auth/register', { email, password }).then((result) => {
        accessToken = result.access_token;
        currentUser = result.user;
        saveAuthToStorage();
        return result;
    });
}
export function login(email, password) {
    return request('/api/v1/auth/login', { email, password }).then((result) => {
        accessToken = result.access_token;
        currentUser = result.user;
        saveAuthToStorage();
        return result;
    });
}
export function logout() {
    accessToken = null;
    currentUser = null;
    saveAuthToStorage();
}
export function getAccessToken() {
    return accessToken;
}
export function getCurrentUser() {
    return currentUser;
}
