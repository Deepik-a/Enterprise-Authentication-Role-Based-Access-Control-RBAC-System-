import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import api, { refreshAccessToken, setAccessToken } from './api';

const AuthContext = createContext();

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
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




    useEffect(() => {
        if (!user) return undefined;
        const refreshVisibleSession = () => {
            if (document.visibilityState === 'visible') fetchMe().catch(() => {});
        };
        window.addEventListener('focus', refreshVisibleSession);
        const timer = window.setInterval(refreshVisibleSession, 30000);
        return () => {
            window.removeEventListener('focus', refreshVisibleSession);
            window.clearInterval(timer);
        };
    }, [user, fetchMe]);

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

        setAccessToken(res.data.access);
    };

    const hasPermission = (codename) => {
        if (!user) return false;
        return user.permissions?.includes(codename) ?? false;
    };
    const hasAnyPermission = (codenames) => codenames.some(hasPermission);

    return (
        <AuthContext.Provider value={{ user, loading, login, logout, changePassword, hasPermission, hasAnyPermission, refreshUser: fetchMe }}>
            {children}
        </AuthContext.Provider>
    );
}

export const useAuth = () => useContext(AuthContext);
