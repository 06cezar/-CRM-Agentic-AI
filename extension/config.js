// Where core-api is reachable. For local dev this is the host machine.
// For a deployed build, point this at your public API origin.
export const API_BASE = "http://localhost:8000";

// The httpOnly auth cookie set by core-api on login. The extension reads it via
// chrome.cookies (JS on the page cannot, because it is httpOnly) and forwards it
// as a Bearer token to the /scraper/ext/* endpoints.
export const AUTH_COOKIE_NAME = "access_token";
