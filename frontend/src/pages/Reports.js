import { useEffect, useState } from 'react';
import api, { errorMessage } from '../api';
import { useAuth } from '../AuthContext';

export default function Reports() {
    const { hasPermission } = useAuth();
    const [report, setReport] = useState(null);
    const [error, setError] = useState('');

    useEffect(() => {
        api.get('reports/summary/')
            .then((res) => setReport(res.data))
            .catch((err) => setError(errorMessage(err, 'Could not load report')));
    }, []);

    const exportCsv = async () => {
        try {
            const res = await api.get('reports/export/', { responseType: 'blob' });
            const url = URL.createObjectURL(res.data);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'orders-report.csv';
            a.click();
            URL.revokeObjectURL(url);
        } catch (err) {
            setError(errorMessage(err, 'Export failed'));
        }
    };

    return (
        <div>
            <h1>Reports</h1>
            {error && <p className="error">{error}</p>}
            {report && (
                <>
                    <p className="muted">Data scope: {report.scope}</p>
                    <div className="stats">
                        <div className="stat"><span>Orders</span><strong>{report.total_orders}</strong></div>
                        <div className="stat"><span>Revenue</span><strong>{report.total_revenue}</strong></div>
                    </div>
                    <table>
                        <thead><tr><th>Status</th><th>Orders</th><th>Revenue</th></tr></thead>
                        <tbody>
                            {report.by_status.map((r) => (
                                <tr key={r.status}><td>{r.status}</td><td>{r.orders}</td><td>{r.revenue}</td></tr>
                            ))}
                        </tbody>
                    </table>
                    {hasPermission('reports_export') && <button className="btn" onClick={exportCsv}>Export CSV</button>}
                </>
            )}
        </div>
    );
}
