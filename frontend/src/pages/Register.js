import { useState } from 'react';
import { Link } from 'react-router-dom';
import api, { errorMessage } from '../api';
import { AuthCard } from './AuthPages';

export default function Register() {
    const [form, setForm] = useState({ email: '', username: '', password: '' });
    const [message, setMessage] = useState('');
    const [error, setError] = useState('');

    const update = (field) => (e) => setForm({ ...form, [field]: e.target.value });

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        try {
            const res = await api.post('auth/register/', form);
            setMessage(res.data.message);
        } catch (err) {
            setError(errorMessage(err, 'Registration failed'));
        }
    };

    return (
        <AuthCard title="Create account">
            {message ? (
                <p className="success">{message}</p>
            ) : (
                <form onSubmit={handleSubmit}>
                    {error && <p className="error">{error}</p>}
                    <label>Email
                        <input type="email" required value={form.email} onChange={update('email')} />
                    </label>
                    <label>Username
                        <input required value={form.username} onChange={update('username')} />
                    </label>
                    <label>Password
                        <input type="password" required value={form.password} onChange={update('password')} />
                    </label>
                    <p className="muted">At least 8 characters, not too common, not all numbers.</p>
                    <button className="btn">Register</button>
                </form>
            )}
            <p>Already have an account? <Link to="/login">Login</Link></p>
        </AuthCard>
    );
}
