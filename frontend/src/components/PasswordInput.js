import { useState } from 'react';

export default function PasswordInput({ label, value, onChange, autoComplete, disabled = false, error = '' }) {
    const [visible, setVisible] = useState(false);
    return <label>{label}
        <span className="password-input">
            <input type={visible ? 'text' : 'password'} value={value} onChange={onChange}
                autoComplete={autoComplete} disabled={disabled} />
            <button type="button" aria-label={visible ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`}
                aria-pressed={visible} onClick={() => setVisible(v => !v)}>{visible ? 'Hide' : 'Show'}</button>
        </span>
        {error && <span className="field-error">{error}</span>}
    </label>;
}
