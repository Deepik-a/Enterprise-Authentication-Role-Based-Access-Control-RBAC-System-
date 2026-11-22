import { useEffect, useState } from 'react';

/** Shows API 403/429 errors raised anywhere in the app (see api.js). */
export default function ErrorBanner() {
    const [message, setMessage] = useState('');

    useEffect(() => {
        let timer;
        const onError = (e) => {
            setMessage(e.detail);
            clearTimeout(timer);
            timer = setTimeout(() => setMessage(''), 6000);
        };
        window.addEventListener('api:error', onError);
        return () => {
            window.removeEventListener('api:error', onError);
            clearTimeout(timer);
        };
    }, []);

    if (!message) return null;
    return (
        <div className="error-banner" role="alert">
            <span>{message}</span>
            <button className="banner-close" onClick={() => setMessage('')} aria-label="Dismiss">×</button>
        </div>
    );
}
