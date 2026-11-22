import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import api, { refreshAccessToken, setAccessToken } from './api';

const AuthContext = createContext();

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null); // { email, roles, permissions, modules, ... }
    const [loading, setLoading] = useState(true);

    const fetchMe = useCallback(async () => {
        const res = await api.get('auth/me/');
        setUser(res.data);
        return res.data;
    }, []);

    const clearSession = useCallback(() => {
        setAccessToken(null);
        setUser(null);
    }, []);

    // On page load the access token is gone (memory only); the refresh cookie
    // silently gets a new one if the session is still valid.
    useEffect(() => {
        (async () => {
            try {
                await refreshAccessToken();
                await fetchMe();
            } catch {
                clearSession();
            } finally {
                setLoading(false);
            }
        })();
        const onLogout = () => clearSession();
        window.addEventListener('auth:logout', onLogout);
        return () => window.removeEventListener('auth:logout', onLogout);
    }, [fetchMe, clearSession]);

    const login = async (email, password) => {
        const res = await api.post('auth/login/', { email, password });
        setAccessToken(res.data.access);
        await fetchMe();
    };

    const logout = async () => {
        try {
            await api.post('auth/logout/');
        } finally {
            clearSession();
        }
    };

    const changePassword = async (oldPassword, newPassword) => {
        const res = await api.post('auth/change-password/', {
            old_password: oldPassword,
            new_password: newPassword,
        });
        // Other sessions were revoked; this one gets a fresh token pair.
        setAccessToken(res.data.access);
    };

    const hasPermission = (codename) => {
        if (!user) return false;
        if (user.is_super_admin) return true;
        return user.permissions?.includes(codename) ?? false;
    };

    return (
        <AuthContext.Provider value={{ user, loading, login, logout, changePassword, hasPermission, refreshUser: fetchMe }}>
            {children}
        </AuthContext.Provider>
    );
}

export const useAuth = () => useContext(AuthContext);
