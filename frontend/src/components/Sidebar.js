import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../AuthContext';

/*
 * The menu comes from `user.modules` returned by /api/auth/me/. The backend
 * only lists modules the user can view, each with its route and order, so
 * adding a module or changing a role changes the menu with no frontend edit.
 */
export default function Sidebar() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();

    const moduleItems = (user?.modules || [])
        .filter((m) => m.route)
        .sort((a, b) => a.order - b.order)
        .map((m) => ({ label: m.name, path: m.route }));

    const items = [
        { label: 'Dashboard', path: '/dashboard' },
        ...moduleItems,
        { label: 'My Profile', path: '/profile' },
        { label: 'Change Password', path: '/change-password' },
    ];

    const handleLogout = async () => {
        await logout();
        navigate('/login');
    };

    return (
        <aside className="sidebar">
            <div className="sidebar-brand">Enterprise Auth</div>
            <div className="sidebar-user">
                <div className="sidebar-email">{user?.email}</div>
                <div className="sidebar-roles">
                    {user?.roles?.length > 0 ? user.roles.join(', ') : 'No role'}
                </div>
            </div>
            <nav>
                {items.map((item) => (
                    <NavLink key={item.path} to={item.path} className="nav-link">
                        {item.label}
                    </NavLink>
                ))}
            </nav>
            <button className="btn btn-secondary sidebar-logout" onClick={handleLogout}>Logout</button>
        </aside>
    );
}
