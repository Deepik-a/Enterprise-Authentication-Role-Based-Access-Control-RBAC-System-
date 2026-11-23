import { Link, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../AuthContext';

export function AccessDenied() {
    return (
        <div className="card access-denied">
            <h2>403 · Access denied</h2>
            <p>Your role doesn't include permission to view this page.</p>
            <p>If you think this is a mistake, ask an administrator to update your roles.</p>
            <Link to="/dashboard">Back to dashboard</Link>
        </div>
    );
}

export default function ProtectedRoute({ children, requiredPermission }) {
    const { user, loading, hasPermission } = useAuth();
    const location = useLocation();

    if (loading) return <p className="muted">Loading...</p>;
    if (!user) return <Navigate to="/login" state={{ from: location.pathname }} replace />;
    if (requiredPermission && !hasPermission(requiredPermission)) {
        return <AccessDenied />;
    }
    return children;
}
