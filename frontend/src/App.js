import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from './AuthContext';
import ErrorBanner from './components/ErrorBanner';
import ProtectedRoute from './components/ProtectedRoute';
import Sidebar from './components/Sidebar';
import AuditLogs from './pages/AuditLogs';
import { Activate, ForgotPassword, ResetPassword } from './pages/AuthPages';
import ChangePassword from './pages/ChangePassword';
import Dashboard from './pages/Dashboard';
import Login from './pages/Login';
import Modules from './pages/Modules';
import MyProfile from './pages/MyProfile';
import Orders from './pages/Orders';
import Permissions from './pages/Permissions';
import Products from './pages/Products';
import Register from './pages/Register';
import Reports from './pages/Reports';
import Roles from './pages/Roles';
import Users from './pages/Users';

/*
 * Page component for each module slug. The *menu* is built from the modules
 * the backend returns (see Sidebar); this registry only says which React
 * component renders a module's route. Access is always `<slug>_view`.
 */
const MODULE_PAGES = {
    user_management: { path: '/users', Component: Users },
    role_management: { path: '/roles', Component: Roles },
    permission_management: { path: '/permissions', Component: Permissions },
    module_management: { path: '/modules', Component: Modules },
    products: { path: '/products', Component: Products },
    orders: { path: '/orders', Component: Orders },
    reports: { path: '/reports', Component: Reports },
    auditlog: { path: '/audit-logs', Component: AuditLogs },
};

function Layout({ children }) {
    return (
        <div className="layout">
            <Sidebar />
            <main className="content">{children}</main>
        </div>
    );
}

function Private({ children, permission }) {
    return (
        // Login check outside the layout, permission check inside it,
        // so the 403 page still shows the sidebar.
        <ProtectedRoute>
            <Layout>
                <ProtectedRoute requiredPermission={permission}>{children}</ProtectedRoute>
            </Layout>
        </ProtectedRoute>
    );
}

function NotFound() {
    const { user } = useAuth();
    if (!user) return <Navigate to="/login" replace />;
    return (
        <Layout>
            <div className="card"><h2>Page not found</h2><p>This page doesn't exist or has no screen yet.</p></div>
        </Layout>
    );
}

export default function App() {
    return (
        <AuthProvider>
            <BrowserRouter>
                <ErrorBanner />
                <Routes>
                    <Route path="/" element={<Navigate to="/dashboard" replace />} />
                    <Route path="/login" element={<Login />} />
                    <Route path="/register" element={<Register />} />
                    <Route path="/forgot-password" element={<ForgotPassword />} />
                    <Route path="/reset-password" element={<ResetPassword />} />
                    <Route path="/activate" element={<Activate />} />

                    <Route path="/dashboard" element={<Private><Dashboard /></Private>} />
                    <Route path="/profile" element={<Private><MyProfile /></Private>} />
                    <Route path="/change-password" element={<Private><ChangePassword /></Private>} />

                    {Object.entries(MODULE_PAGES).map(([slug, { path, Component }]) => (
                        <Route key={slug} path={path} element={<Private permission={`${slug}_view`}><Component /></Private>} />
                    ))}

                    <Route path="*" element={<NotFound />} />
                </Routes>
            </BrowserRouter>
        </AuthProvider>
    );
}
