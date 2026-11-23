import { useCallback, useEffect, useState } from 'react';
import api, { errorMessage } from '../api';
import { useAuth } from '../AuthContext';
import { useSweetAlert } from '../components/SweetAlert';

export default function Products() {
    const { hasPermission } = useAuth();
    const { alert, confirm } = useSweetAlert();
    const [products, setProducts] = useState([]);
    const [form, setForm] = useState({ name: '', price: '', description: '' });
    const [editing, setEditing] = useState(null);
    const [error, setError] = useState('');
    const formErrors = { name: form.name.trim() ? '' : 'Product name is required.', price: Number(form.price) > 0 ? '' : 'Enter a price greater than zero.' };
    const editErrors = editing ? { name: editing.name.trim() ? '' : 'Product name is required.', price: Number(editing.price) > 0 ? '' : 'Enter a price greater than zero.' } : {};

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
        if (!await confirm('Delete product?', 'Are you sure you want to delete this product?')) return;
        try {
            await api.delete(`products/${id}/`);
            load();
        } catch (err) {
            setError(errorMessage(err, 'Could not delete product'));
        }
    };

    const saveEdit = async () => {
        setError('');
        try {
            await api.patch(`products/${editing.id}/`, {
                name: editing.name,
                price: editing.price,
                description: editing.description,
            });
            setEditing(null);
            load();
        } catch (err) {
            setError(errorMessage(err, 'Could not update product'));
        }
    };

    const order = async (id) => {
        try {
            await api.post('orders/', { product: id, quantity: 1 });
            await alert('Order placed', 'Your order was submitted.');
        } catch (err) {
            setError(errorMessage(err, 'Could not place order'));
        }
    };

    return (
        <div>
            <h1>Products</h1>
            {error && <p className="error">{error}</p>}
            {hasPermission('products_create') && (
                <form className="card inline-form" onSubmit={create} noValidate>
                    <label>Name<input placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
                    {form.name && formErrors.name && <span className="field-error">{formErrors.name}</span>}</label>
                    <label>Price<input placeholder="Price" type="text" inputMode="decimal" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} />
                    {form.price && formErrors.price && <span className="field-error">{formErrors.price}</span>}</label>
                    <input placeholder="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
                    <button className="btn" disabled={Object.values(formErrors).some(Boolean)}>Add product</button>
                </form>
            )}
            <table>
                <thead><tr><th>ID</th><th>Name</th><th>Price</th><th>Description</th><th>Actions</th></tr></thead>
                <tbody>
                    {products.map((p) => (
                        <tr key={p.id}>
                            <td>{p.id}</td>
                            <td>{editing?.id === p.id ? <><input value={editing.name}
                                onChange={(e) => setEditing({ ...editing, name: e.target.value })} />{editing.id === p.id && editErrors.name && <span className="field-error">{editErrors.name}</span>}</> : p.name}</td>
                            <td>{editing?.id === p.id ? <><input type="text" inputMode="decimal" value={editing.price}
                                onChange={(e) => setEditing({ ...editing, price: e.target.value })} />{editing.id === p.id && editErrors.price && <span className="field-error">{editErrors.price}</span>}</> : p.price}</td>
                            <td>{editing?.id === p.id ? <input value={editing.description}
                                onChange={(e) => setEditing({ ...editing, description: e.target.value })} /> : p.description}</td>
                            <td>
                                {editing?.id === p.id ? (
                                    <>
                                        <button className="btn btn-small" onClick={saveEdit} disabled={Object.values(editErrors).some(Boolean)}>Save</button>
                                        <button className="btn btn-small" onClick={() => setEditing(null)}>Cancel</button>
                                    </>
                                ) : (
                                    <>
                                        {hasPermission('orders_create') && <button className="btn btn-small" onClick={() => order(p.id)}>Order</button>}
                                        {hasPermission('products_edit') && <button className="btn btn-small" onClick={() => setEditing({ ...p })}>Edit</button>}
                                        {hasPermission('products_delete') && <button className="btn btn-small btn-danger" onClick={() => remove(p.id)}>Delete</button>}
                                    </>
                                )}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
