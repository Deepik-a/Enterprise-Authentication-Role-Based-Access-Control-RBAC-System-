import { useState, useEffect } from 'react';
import api from '../api';

export default function AuditLogs() {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchLogs = async () => {
        try {
            const res = await api.get('auditlogs/');
            setLogs(res.data.results || res.data || []);
        } catch (err) {
            console.error('Failed to fetch audit logs', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchLogs();
    }, []);

    return (
        <div>
            <h1>Audit Logs</h1>
            <p>Who changed which users, roles, permissions and modules, and when.</p>
            {loading ? (
                <p>Loading audit logs...</p>
            ) : (
                <table border="1">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Action</th>
                            <th>Actor</th>
                            <th>Timestamp</th>
                            <th>Object type</th>
                            <th>Object</th>
                            <th>Changes</th>
                        </tr>
                    </thead>
                    <tbody>
                        {logs.length === 0 ? (
                            <tr>
                                <td colSpan="7">No audit records found yet.</td>
                            </tr>
                        ) : (
                            logs.map(log => (
                                <tr key={log.id}>
                                    <td>{log.id}</td>
                                    <td>{log.action}</td>
                                    <td>{log.actor_email || 'System'}</td>
                                    <td>{new Date(log.timestamp).toLocaleString()}</td>
                                    <td>{log.object_type}</td>
                                    <td>{log.object_repr || log.object_id}</td>
                                    <td>{JSON.stringify(log.changes || {})}</td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            )}
        </div>
    );
}
