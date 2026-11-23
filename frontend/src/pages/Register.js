import { useState } from 'react';
import { Link } from 'react-router-dom';
import api, { errorMessage } from '../api';
import { AuthCard } from './AuthPages';
import PasswordInput from '../components/PasswordInput';

export default function Register() {
    const [form, setForm] = useState({ email: '', username: '', password: '' });
    const [fieldErrors, setFieldErrors] = useState({});
    const [otp, setOtp] = useState('');
    const [step, setStep] = useState('details');
    const [message, setMessage] = useState('');
    const [error, setError] = useState('');
    const [busy, setBusy] = useState(false);
    const [liveErrors, setLiveErrors] = useState({});

    const update = (field) => (e) => {
        const value = e.target.value;
        setForm({ ...form, [field]: value });
        const nextErrors = { ...liveErrors };
        if (field === 'email') nextErrors.email = value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) ? 'Enter a valid email address.' : '';
        if (field === 'username') nextErrors.username = value.trim().length < 3 ? 'Username must be at least 3 characters.' : '';
        if (field === 'password') nextErrors.password = value.length < 8 ? 'Password must be at least 8 characters.' : '';
        setLiveErrors(nextErrors);
        if (fieldErrors[field]) {
            setFieldErrors({ ...fieldErrors, [field]: null });
        }
    };

    const extractFieldErrors = (err) => {
        const data = err?.response?.data;
        if (data && typeof data === 'object' && !data.detail && !data.error) {
            const extracted = {};
            for (const [key, val] of Object.entries(data)) {
                extracted[key] = Array.isArray(val) ? val.join(' ') : String(val);
            }
            return extracted;
        }
        return {};
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setMessage('');
        setFieldErrors({});
        setBusy(true);
        try {
            const res = await api.post('auth/register/', form);
            setMessage(res.data.message);
            setStep('otp');
            setOtp('');
        } catch (err) {
            setFieldErrors(extractFieldErrors(err));
            setError(errorMessage(err, 'Registration failed'));
        } finally {
            setBusy(false);
        }
    };

    const handleVerify = async (e) => {
        e.preventDefault();
        setError('');
        setMessage('');
        setBusy(true);
        try {
            const res = await api.post('auth/verify-otp/', { email: form.email, otp });
            setMessage(res.data.message);
            setStep('done');
        } catch (err) {
            setError(errorMessage(err, 'Verification failed'));
        } finally {
            setBusy(false);
        }
    };

    const handleResend = async () => {
        setError('');
        setMessage('');
        setBusy(true);
        try {
            const res = await api.post('auth/resend-otp/', { email: form.email });
            setMessage(res.data.message);
        } catch (err) {
            setError(errorMessage(err, 'Could not resend the code'));
        } finally {
            setBusy(false);
        }
    };

    const startOver = () => {
        setStep('details');
        setOtp('');
        setError('');
        setMessage('');
        setFieldErrors({});
    };

    const isExpired = error.toLowerCase().includes('expired') || error.toLowerCase().includes('register again');

    return (
        <AuthCard title="Create account">
            {step === 'done' ? (
                <div>
                    <p className="success">{message}</p>
                    <p style={{ marginTop: '16px' }}>
                        <Link to="/login" className="btn" style={{ display: 'inline-block', textDecoration: 'none' }}>
                            Go to Login
                        </Link>
                    </p>
                </div>
            ) : step === 'otp' ? (
                <form onSubmit={handleVerify} noValidate>
                    {message && <p className="success">{message}</p>}
                    {error && <p className="error">{error}</p>}
                    <p className="muted">
                        Enter the 6-digit code sent to <strong>{form.email}</strong>. It expires in 10 minutes.
                    </p>
                    {isExpired ? (
                        <div style={{ marginTop: '12px', marginBottom: '12px' }}>
                            <p className="muted">Your session has expired. Please restart registration.</p>
                            <button type="button" className="btn" onClick={startOver}>
                                Register again
                            </button>
                        </div>
                    ) : (
                        <>
                            <label>Verification code
                                <input
                                    inputMode="numeric"
                                    autoComplete="one-time-code"
                                    pattern="[0-9]{6}"
                                    maxLength={6}
                                    value={otp}
                                    onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                                />
                            </label>
                            <button className="btn" disabled={busy || otp.length !== 6}>Verify</button>
                            <button type="button" onClick={handleResend} disabled={busy}>Resend code</button>
                            <p><button type="button" onClick={startOver}>Use different details</button></p>
                        </>
                    )}
                </form>
            ) : (
                <form onSubmit={handleSubmit} noValidate>
                    {error && <p className="error">{error}</p>}
                    <label>Email
                        <input
                            type="text"
                            value={form.email}
                            onChange={update('email')}
                        />
                        {fieldErrors.email && <span className="error" style={{ display: 'block', marginTop: '4px', fontSize: '12px' }}>{fieldErrors.email}</span>}
                        {liveErrors.email && <span className="field-error">{liveErrors.email}</span>}
                    </label>
                    <label>Username
                        <input
                            value={form.username}
                            onChange={update('username')}
                        />
                        {fieldErrors.username && <span className="error" style={{ display: 'block', marginTop: '4px', fontSize: '12px' }}>{fieldErrors.username}</span>}
                        {liveErrors.username && <span className="field-error">{liveErrors.username}</span>}
                    </label>
                    <PasswordInput label="Password" value={form.password} onChange={update('password')} autoComplete="new-password" />
                    {fieldErrors.password && <span className="field-error">{fieldErrors.password}</span>}
                    {liveErrors.password && <span className="field-error">{liveErrors.password}</span>}
                    <p className="muted">At least 8 characters, not too common, not all numbers.</p>
                    <button className="btn" disabled={busy || !form.email || !form.username || !form.password || Object.values(liveErrors).some(Boolean)}>Register</button>
                </form>
            )}
            <p>Already have an account? <Link to="/login">Login</Link></p>
        </AuthCard>
    );
}
