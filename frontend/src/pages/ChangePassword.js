import { useState } from 'react';
import { errorMessage } from '../api';
import { useAuth } from '../AuthContext';
import PasswordInput from '../components/PasswordInput';
import { passwordPolicyError } from '../passwordValidation';

export default function ChangePassword() {
    const { changePassword } = useAuth();
    const [form, setForm] = useState({ old: '', next: '', confirm: '' });
    const [error, setError] = useState('');
    const [message, setMessage] = useState('');

    const update = (field) => (e) => setForm({ ...form, [field]: e.target.value });

    const submit = async (e) => {
        e.preventDefault();
        setError('');
        setMessage('');
        if (form.next !== form.confirm) {
            setError('New passwords do not match');
            return;
        }
        try {
            await changePassword(form.old, form.next);
            setMessage('Password changed. You were signed out on all other devices.');
            setForm({ old: '', next: '', confirm: '' });
        } catch (err) {
            setError(errorMessage(err, 'Could not change password'));
        }
    };

    return (
        <div className="card narrow">
            <h1>Change password</h1>
            {error && <p className="error">{error}</p>}
            {message && <p className="success">{message}</p>}
            <form onSubmit={submit} noValidate>
                <PasswordInput label="Current password" value={form.old} onChange={update('old')} autoComplete="current-password" />
                <PasswordInput label="New password" value={form.next} onChange={update('next')} autoComplete="new-password"
                    error={form.next ? passwordPolicyError(form.next) : ''} />
                <PasswordInput label="Confirm new password" value={form.confirm} onChange={update('confirm')} autoComplete="new-password"
                    error={form.confirm && form.next !== form.confirm ? 'Passwords do not match.' : ''} />
                <button className="btn" disabled={!form.old || !!passwordPolicyError(form.next) || form.next !== form.confirm}>Change password</button>
            </form>
        </div>
    );
}
