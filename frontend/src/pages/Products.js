import { useCallback, useEffect, useState } from 'react';
import api, { errorMessage } from '../api';
import { useAuth } from '../AuthContext';

export default function Products() {
    const { hasPermission } = useAuth();
    const [products, setProducts] = useState([]);
    const [form, setForm] = useState({ name: '', price: '', description: '' });
    const [error, setError] = useState('');

    const load = useCallback(async () => {
        const res = await api.get('products/');
        setProducts(res.data.results || res.data);
    }, []);

    useEffect(() => { load().catch(() => {}); }, [load]);

    const create = async (e) => {
        e.preventDefault();
        setError('');
        try {
            await api.post('products/', form);
            setForm({ name: '', price: '', description: '' });
            load();
        } catch (err) {
            setError(errorMessage(err, 'Could not create product'));
        }
    };

    const remove = async (id) => {
        if (!window.confirm('Delete this product?')) return;
        try {
            await api.delete(`products/${id}/`);
            load();
        } catch (err) {
            setError(errorMessage(err, 'Could not delete product'));
        }
    };

    const order = async (id) => {
        try {
            await api.post('orders/', { product: id, quantity: 1 });
            alert('Order placed');
        } catch (err) {
            setError(errorMessage(err, 'Could not place order'));
        }
    };

    return (
        <div>
            <h1>Products</h1>
            {error && <p className="error">{error}</p>}
            {hasPermission('products_create') && (
                <form className="card inline-form" onSubmit={create}>
                    <input placeholder="Name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
                    <input placeholder="Price" type="number" step="0.01" min="0" required value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} />
                    <input placeholder="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
                    <button className="btn">Add product</button>
                </form>
            )}
            <table>
                <thead><tr><th>ID</th><th>Name</th><th>Price</th><th>Description</th><th>Actions</th></tr></thead>
                <tbody>
                    {products.map((p) => (
                        <tr key={p.id}>
                            <td>{p.id}</td>
                            <td>{p.name}</td>
                            <td>{p.price}</td>
                            <td>{p.description}</td>
                            <td>
                                {hasPermission('orders_create') && <button className="btn btn-small" onClick={() => order(p.id)}>Order</button>}
                                {hasPermission('products_delete') && <button className="btn btn-small btn-danger" onClick={() => remove(p.id)}>Delete</button>}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
