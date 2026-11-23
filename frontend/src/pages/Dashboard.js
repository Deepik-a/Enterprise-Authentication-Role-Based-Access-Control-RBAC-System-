import { useEffect, useState } from 'react';
import api from '../api';
import { useAuth } from '../AuthContext';

const LABELS = { users: 'Users', roles: 'Roles', modules: 'Modules', products: 'Products', orders: 'Orders' };

export default function Dashboard() {
    const { user } = useAuth();
    const [stats, setStats] = useState({});

    useEffect(() => {

        api.get('dashboard/stats/')
            .then((res) => setStats(res.data))
            .catch((err) => console.error('Failed to fetch dashboard stats', err));
    }, []);

    return (
        <div>
            <h1>Welcome, {user?.username}</h1>
            <p className="muted">Roles: {user?.roles?.join(', ') || 'none'}</p>
            <div className="stats">
                {Object.entries(stats).map(([key, value]) => (
                    <div className="stat" key={key}>
                        <span>{LABELS[key] || key}</span>
                        <strong>{value}</strong>
                    </div>
                ))}
            </div>
        </div>
    );
}
