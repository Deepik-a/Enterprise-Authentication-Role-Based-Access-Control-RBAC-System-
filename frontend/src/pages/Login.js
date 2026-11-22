import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { errorMessage } from '../api';
import { useAuth } from '../AuthContext';
import { AuthCard } from './AuthPages';

export default function Login() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [busy, setBusy] = useState(false);
    const { user, login } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();

    if (user) return <Navigate to="/dashboard" replace />;

    const handleSubmit = async (e) => {
        e.preventDefault();
        setBusy(true);
        setError('');
        try {
            await login(email, password);
            navigate(location.state?.from || '/dashboard');
        } catch (err) {
            setError(errorMessage(err, 'Invalid credentials'));
        } finally {
            setBusy(false);
        }
    };

    return (
        <AuthCard title="Sign in">
            {error && <p className="error">{error}</p>}
            <form onSubmit={handleSubmit}>
                <label>Email
                    <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
                </label>
                <label>Password
                    <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} />
                </label>
                <button className="btn" disabled={busy}>Login</button>
            </form>
            <p><Link to="/forgot-password">Forgot password?</Link></p>
            <p>No account? <Link to="/register">Register</Link></p>
        </AuthCard>
    );
}
