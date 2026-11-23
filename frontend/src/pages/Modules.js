import { useState, useEffect } from 'react';
import api, { errorMessage } from '../api';
import { useAuth } from '../AuthContext';
import { useSweetAlert } from '../components/SweetAlert';

export default function Modules() {
    const [modules, setModules] = useState([]);
    const [form, setForm] = useState({ name: '', slug: '', route: '', order: 100 });
    const [editModule, setEditModule] = useState(null);
    const { hasPermission } = useAuth();
    const { alert, confirm } = useSweetAlert();
    const formError = !form.name.trim() ? 'Module name is required.' : '';
    const editNameError = editModule && !editModule.name.trim() ? 'Module name is required.' : '';
    const orderError = (value) => /^\d+$/.test(String(value)) ? '' : 'Menu order must be a non-negative whole number.';
    const routeError = (value) => !value || value.startsWith('/') ? '' : 'Route must start with /.';

    const fetchModules = async () => {
        try {
            const res = await api.get('modules/');
            setModules(res.data.results || res.data);
        } catch (err) {
            console.error('Failed to fetch modules', err);
        }
    };

    useEffect(() => {
        fetchModules();
    }, []);

    const createModule = async (e) => {
        e.preventDefault();
        try {
            await api.post('modules/', form);
            setForm({ name: '', slug: '', route: '', order: 100 });
            fetchModules();
        } catch (err) {
            await alert('Could not create module', errorMessage(err, 'Failed to create module'));
        }
    };

    const deleteModule = async (id) => {
        if (!await confirm('Delete module?', 'Are you sure you want to delete this module?')) return;
        try {
            await api.delete(`modules/${id}/`);
            fetchModules();
        } catch (err) {
            await alert('Could not delete module', errorMessage(err, 'Failed to delete module'));
        }
    };

    const saveEdit = async (e) => {
        e.preventDefault();
        try {
            await api.patch(`modules/${editModule.id}/`, {
                name: editModule.name,
                slug: editModule.slug,
                route: editModule.route,
                order: Number(editModule.order),
            });
            setEditModule(null);
            fetchModules();
        } catch (err) {
            await alert('Could not update module', errorMessage(err, 'Failed to update module'));
        }
    };

    return (
        <div>
            <h1>Modules</h1>
            {hasPermission('module_management_create') && (
                <form onSubmit={createModule} noValidate style={{ marginBottom: '1rem' }}>
                    <input
                        placeholder="Module Name"
                        value={form.name}
                        onChange={e => setForm({ ...form, name: e.target.value })}
                    />
                    {form.name && formError && <span className="field-error">{formError}</span>}
                    <input placeholder="Slug (optional)" value={form.slug}
                        onChange={e => setForm({ ...form, slug: e.target.value })} />
                    {form.slug && !/^[a-z0-9_]+$/i.test(form.slug) && <span className="field-error">Slug can contain letters, numbers, and underscores.</span>}
                    <input placeholder="Route (e.g. /reports)" value={form.route}
                        onChange={e => setForm({ ...form, route: e.target.value })} />
                    {routeError(form.route) && <span className="field-error">{routeError(form.route)}</span>}
                    <input type="text" inputMode="numeric" placeholder="Menu order" value={form.order}
                        onChange={e => setForm({ ...form, order: e.target.value })} />
                    {form.order !== '' && orderError(form.order) && <span className="field-error">{orderError(form.order)}</span>}
                    <button type="submit" disabled={!!formError || (!!form.slug && !/^[a-z0-9_]+$/i.test(form.slug)) || !!routeError(form.route) || !!orderError(form.order)}>Create Module</button>
                </form>
            )}

            <table border="1">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {modules.map(m => (
                        <tr key={m.id}>
                            <td>{m.id}</td>
                            <td>
                                {editModule?.id === m.id ? (
                                    <form onSubmit={saveEdit} noValidate>
                                        <input value={editModule.name}
                                            onChange={e => setEditModule({ ...editModule, name: e.target.value })} />
                                        {editNameError && <span className="field-error">{editNameError}</span>}
                                        <input value={editModule.slug || ''} disabled={m.is_system}
                                            onChange={e => setEditModule({ ...editModule, slug: e.target.value })} />
                                        {editModule.slug && !/^[a-z0-9_]+$/i.test(editModule.slug) && <span className="field-error">Slug can contain letters, numbers, and underscores.</span>}
                                        <input value={editModule.route || ''} placeholder="Route"
                                            onChange={e => setEditModule({ ...editModule, route: e.target.value })} />
                                        {routeError(editModule.route || '') && <span className="field-error">{routeError(editModule.route || '')}</span>}
                                        <input type="text" inputMode="numeric" value={editModule.order}
                                            onChange={e => setEditModule({ ...editModule, order: e.target.value })} />
                                        {editModule.order !== '' && orderError(editModule.order) && <span className="field-error">{orderError(editModule.order)}</span>}
                                        <button type="submit" disabled={!!editNameError || (!!editModule.slug && !/^[a-z0-9_]+$/i.test(editModule.slug)) || !!routeError(editModule.route || '') || !!orderError(editModule.order)}>Save</button>
                                        <button type="button" onClick={() => setEditModule(null)}>Cancel</button>
                                    </form>
                                ) : (
                                    <>{m.name} <small>({m.slug}, {m.route || 'no route'})</small></>
                                )}
                            </td>
                            <td>
                                {editModule?.id !== m.id && (
                                    <>
                                        {hasPermission('module_management_edit') && (
                                            <button onClick={() => setEditModule({ ...m })}>Edit</button>
                                        )}
                                        {hasPermission('module_management_delete') && !m.is_system && (
                                            <button onClick={() => deleteModule(m.id)}>Delete</button>
                                        )}
                                        {m.is_system && <span>System protected</span>}
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
