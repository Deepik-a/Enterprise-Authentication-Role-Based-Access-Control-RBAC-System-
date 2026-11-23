import { useCallback, useEffect, useState } from 'react';
import api, { errorMessage } from '../api';
import { useAuth } from '../AuthContext';

const STATUSES = ['pending', 'approved', 'shipped', 'cancelled'];
const SCOPE_TEXT = {
    all: 'You can see all orders.',
    team: "You can see your own orders and your team's orders.",
    own: 'You can see only your own orders.',
};

export default function Orders() {
    const { user, hasPermission } = useAuth();
    const [orders, setOrders] = useState([]);
    const [error, setError] = useState('');

    const load = useCallback(async () => {
        const res = await api.get('orders/');
        setOrders(res.data.results || res.data);
    }, []);

    useEffect(() => { load().catch(() => {}); }, [load]);

    const act = async (fn, fallback) => {
        setError('');
        try {
            await fn();
            load();
        } catch (err) {
            setError(errorMessage(err, fallback));
        }
    };

    return (
        <div>
            <h1>Orders</h1>
            <p className="muted">{SCOPE_TEXT[user?.data_scope]}</p>
            {error && <p className="error">{error}</p>}
            <table>
                <thead>
                    <tr><th>ID</th><th>Customer</th><th>Product</th><th>Qty</th><th>Total</th><th>Status</th><th>Actions</th></tr>
                </thead>
                <tbody>
                    {orders.length === 0 && <tr><td colSpan="7">No orders.</td></tr>}
                    {orders.map((o) => (
                        <tr key={o.id}>
                            <td>{o.id}</td>
                            <td>{o.customer_email}</td>
                            <td>{o.product_name}</td>
                            <td>{o.quantity}</td>
                            <td>{o.total}</td>
                            <td>
                                {hasPermission('orders_edit') ? (
                                    <select value={o.status} onChange={(e) => act(
                                        () => api.patch(`orders/${o.id}/`, { status: e.target.value }), 'Could not update order')}>
                                        {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                                    </select>
                                ) : o.status}
                            </td>
                            <td>
                                {hasPermission('orders_cancel') && o.status === 'pending' && (
                                    <button className="btn btn-small btn-danger" onClick={() => act(
                                        () => api.post(`orders/${o.id}/cancel/`), 'Could not cancel order')}>Cancel</button>
                                )}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
