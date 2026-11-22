import { useState } from 'react';
import { errorMessage } from '../api';
import { useAuth } from '../AuthContext';

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
            <form onSubmit={submit}>
                <label>Current password
                    <input type="password" required value={form.old} onChange={update('old')} />
                </label>
                <label>New password
                    <input type="password" required value={form.next} onChange={update('next')} />
                </label>
                <label>Confirm new password
                    <input type="password" required value={form.confirm} onChange={update('confirm')} />
                </label>
                <button className="btn">Change password</button>
            </form>
        </div>
    );
}
