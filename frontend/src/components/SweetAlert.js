import { createContext, useContext, useState } from 'react';

const SweetAlertContext = createContext(null);

export function SweetAlertProvider({ children }) {
    const [dialog, setDialog] = useState(null);
    const show = (title, text = '', confirm = false) => new Promise(resolve => {
        setDialog({ title, text, confirm, resolve });
    });
    const close = (value) => {
        dialog?.resolve(value);
        setDialog(null);
    };

    return (
        <SweetAlertContext.Provider value={{ alert: (title, text) => show(title, text), confirm: (title, text) => show(title, text, true) }}>
            {children}
            {dialog && <div className="swal-backdrop" role="presentation">
                <section className="swal-dialog" role="alertdialog" aria-modal="true" aria-labelledby="swal-title">
                    <div className={`swal-mark ${dialog.confirm ? 'swal-warning' : 'swal-success'}`} aria-hidden="true">{dialog.confirm ? '!' : '✓'}</div>
                    <h2 id="swal-title">{dialog.title}</h2>
                    {dialog.text && <p>{dialog.text}</p>}
                    <div className="swal-actions">
                        {dialog.confirm && <button type="button" className="btn btn-secondary" onClick={() => close(false)}>Cancel</button>}
                        <button type="button" className="btn" autoFocus onClick={() => close(true)}>{dialog.confirm ? 'Confirm' : 'OK'}</button>
                    </div>
                </section>
            </div>}
        </SweetAlertContext.Provider>
    );
}

export function useSweetAlert() {
    const value = useContext(SweetAlertContext);
    if (!value) throw new Error('useSweetAlert must be used inside SweetAlertProvider');
    return value;
}
