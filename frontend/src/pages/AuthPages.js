
import { useEffect, useRef, useState } from 'react';
import { Link, Navigate, useSearchParams } from 'react-router-dom';
import api, { errorMessage } from '../api';
import PasswordInput from '../components/PasswordInput';

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
    const [otp, setOtp] = useState('');
    const [password, setPassword] = useState('');
    const [confirm, setConfirm] = useState('');
    const [step, setStep] = useState('request');
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
            setStep('reset');
        } catch (err) {
            setError(errorMessage(err, 'Could not send the reset email'));
        } finally {
            setBusy(false);
        }
    };

    const reset = async (e) => {
        e.preventDefault();
        setError('');
        if (password !== confirm) {
            setError('Passwords do not match');
            return;
        }
        setBusy(true);
        try {
            const res = await api.post('auth/reset-password/', { email, otp, new_password: password });
            setMessage(res.data.message);
            setStep('done');
        } catch (err) {
            setError(errorMessage(err, 'Password reset failed'));
        } finally {
            setBusy(false);
        }
    };

    return (
        <AuthCard title="Forgot password">
            {step === 'request' ? (
                <form onSubmit={submit} noValidate>
                    {error && <p className="error">{error}</p>}
                    <label>Email
                        <input type="text" value={email} onChange={(e) => setEmail(e.target.value)} />
                        {email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) && <span className="field-error">Enter a valid email address.</span>}
                    </label>
                    <button className="btn" disabled={busy || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)}>Send verification code</button>
                </form>
            ) : step === 'reset' ? (
                <form onSubmit={reset} noValidate>
                    <p>{message}</p>
                    {error && <p className="error">{error}</p>}
                    <label>Email verification code
                        <input inputMode="numeric" autoComplete="one-time-code" maxLength={6}
                            value={otp} onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))} />
                    </label>
                    <PasswordInput label="New password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password"
                        error={password && password.length < 8 ? 'Password must be at least 8 characters.' : ''} />
                    <PasswordInput label="Confirm new password" value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password"
                        error={confirm && password !== confirm ? 'Passwords do not match.' : ''} />
                    <button className="btn" disabled={busy || otp.length !== 6 || password.length < 8 || password !== confirm}>Reset password</button>
                </form>
            ) : <p className="success">{message}</p>}
            <p><Link to="/login">Back to login</Link></p>
        </AuthCard>
    );
}

export function ResetPassword() {
    return <Navigate to="/forgot-password" replace />;
}

export function Activate() {
    const [params] = useSearchParams();
    const token = params.get('token') || '';
    const [state, setState] = useState({ status: 'pending', message: 'Activating your account...' });
    const sent = useRef(false);

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
