// Public auth pages: forgot password, reset password, account activation.
import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import api, { errorMessage } from '../api';

export function AuthCard({ title, children }) {
    return (
        <div className="auth-page">
            <div className="card auth-card">
                <h1>{title}</h1>
                {children}
            </div>
        </div>
    );
}

export function ForgotPassword() {
    const [email, setEmail] = useState('');
    const [message, setMessage] = useState('');
    const [error, setError] = useState('');
    const [busy, setBusy] = useState(false);

    const submit = async (e) => {
        e.preventDefault();
        setBusy(true);
        setError('');
        try {
            const res = await api.post('auth/forgot-password/', { email });
            setMessage(res.data.message);
        } catch (err) {
            setError(errorMessage(err, 'Could not send the reset email'));
        } finally {
            setBusy(false);
        }
    };

    return (
        <AuthCard title="Forgot password">
            {message ? (
                <p className="success">{message}</p>
            ) : (
                <form onSubmit={submit}>
                    {error && <p className="error">{error}</p>}
                    <label>Email
                        <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
                    </label>
                    <button className="btn" disabled={busy}>Send reset link</button>
                </form>
            )}
            <p><Link to="/login">Back to login</Link></p>
        </AuthCard>
    );
}

export function ResetPassword() {
    const [params] = useSearchParams();
    const token = params.get('token') || '';
    const [password, setPassword] = useState('');
    const [confirm, setConfirm] = useState('');
    const [error, setError] = useState('');
    const [done, setDone] = useState(false);
    const navigate = useNavigate();

    const submit = async (e) => {
        e.preventDefault();
        if (password !== confirm) {
            setError('Passwords do not match');
            return;
        }
        try {
            await api.post('auth/reset-password/', { token, new_password: password });
            setDone(true);
            setTimeout(() => navigate('/login'), 2000);
        } catch (err) {
            setError(errorMessage(err, 'Reset failed'));
        }
    };

    if (!token) {
        return <AuthCard title="Reset password"><p className="error">This reset link is missing its token.</p></AuthCard>;
    }
    return (
        <AuthCard title="Choose a new password">
            {done ? (
                <p className="success">Password reset. Redirecting to login...</p>
            ) : (
                <form onSubmit={submit}>
                    {error && <p className="error">{error}</p>}
                    <label>New password
                        <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} />
                    </label>
                    <label>Confirm password
                        <input type="password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} />
                    </label>
                    <button className="btn">Reset password</button>
                </form>
            )}
        </AuthCard>
    );
}

export function Activate() {
    const [params] = useSearchParams();
    const token = params.get('token') || '';
    const [state, setState] = useState({ status: 'pending', message: 'Activating your account...' });
    const sent = useRef(false); // tokens are single-use; don't double-submit in StrictMode

    useEffect(() => {
        if (sent.current) return;
        sent.current = true;
        api.post('auth/activate/', { token })
            .then((res) => setState({ status: 'ok', message: res.data.message }))
            .catch((err) => setState({ status: 'error', message: errorMessage(err, 'Activation failed') }));
    }, [token]);

    return (
        <AuthCard title="Account activation">
            <p className={state.status === 'error' ? 'error' : state.status === 'ok' ? 'success' : 'muted'}>
                {state.message}
            </p>
            <p><Link to="/login">Go to login</Link></p>
        </AuthCard>
    );
}
