import axios from 'axios';

export const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/';








let accessToken = null;
export const setAccessToken = (token) => { accessToken = token; };
export const getAccessToken = () => accessToken;

const api = axios.create({
    baseURL: API_BASE,
    withCredentials: true,
});

api.interceptors.request.use((config) => {
    if (accessToken) {
        config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
});



let refreshPromise = null;

export function refreshAccessToken() {
    if (!refreshPromise) {
        refreshPromise = axios
            .post(`${API_BASE}auth/token/refresh/`, {}, { withCredentials: true })
            .then((res) => {
                setAccessToken(res.data.access);
                return res.data.access;
            })
            .catch((err) => {
                setAccessToken(null);
                throw err;
            })
            .finally(() => {
                refreshPromise = null;
            });
    }
    return refreshPromise;
}

const AUTH_PATHS = ['auth/login/', 'auth/token/refresh/', 'auth/register/', 'auth/verify-otp/',
    'auth/resend-otp/', 'auth/forgot-password/', 'auth/reset-password/', 'auth/activate/',
    'auth/resend-activation/'];

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const original = error.config || {};
        const status = error.response?.status;
        const isAuthCall = AUTH_PATHS.some((p) => original.url?.includes(p));

        if (status === 401 && !original._retry && !isAuthCall) {
            original._retry = true;
            try {
                const token = await refreshAccessToken();
                original.headers.Authorization = `Bearer ${token}`;
                return api(original);
            } catch {
                window.dispatchEvent(new CustomEvent('auth:logout'));
            }
        }

        if (status === 403) {
            window.dispatchEvent(new CustomEvent('api:error', {
                detail: error.response?.data?.detail || "You don't have permission to perform this action.",
            }));
        } else if (status === 429) {
            window.dispatchEvent(new CustomEvent('api:error', {
                detail: 'Too many attempts. Please wait a moment and try again.',
            }));
        }
        return Promise.reject(error);
    }
);


export function errorMessage(err, fallback = 'Something went wrong') {
    const data = err?.response?.data;
    if (!data) return err?.message || fallback;
    if (typeof data === 'string') return fallback;
    if (data.detail) return data.detail;
    if (data.error) return data.error;
    return Object.entries(data)
        .map(([field, msgs]) => `${field}: ${Array.isArray(msgs) ? msgs.join(' ') : msgs}`)
        .join(' | ');
}

export default api;
