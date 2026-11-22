import { useState, useEffect } from 'react';
import api, { errorMessage } from '../api';
import { useAuth } from '../AuthContext';

export default function Modules() {
    const [modules, setModules] = useState([]);
    const [name, setName] = useState('');
    const [editId, setEditId] = useState(null);
    const [editName, setEditName] = useState('');
    const { hasPermission } = useAuth();

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
            await api.post('modules/', { name });
            setName('');
            fetchModules();
        } catch (err) {
            alert(errorMessage(err, 'Failed to create module'));
        }
    };

    const deleteModule = async (id) => {
        if (!window.confirm('Are you sure you want to delete this module?')) return;
        try {
            await api.delete(`modules/${id}/`);
            fetchModules();
        } catch (err) {
            alert(errorMessage(err, 'Failed to delete module'));
        }
    };

    const startEdit = (mod) => {
        setEditId(mod.id);
        setEditName(mod.name);
    };

    const saveEdit = async (id) => {
        try {
            await api.put(`modules/${id}/`, { name: editName });
            setEditId(null);
            fetchModules();
        } catch (err) {
            alert(errorMessage(err, 'Failed to update module'));
        }
    };

    return (
        <div>
            <h1>Modules</h1>
            {hasPermission('module_management_create') && (
                <form onSubmit={createModule} style={{ marginBottom: '1rem' }}>
                    <input
                        placeholder="Module Name"
                        value={name}
                        onChange={e => setName(e.target.value)}
                        required
                    />
                    <button type="submit">Create Module</button>
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
                                {editId === m.id ? (
                                    <input
                                        value={editName}
                                        onChange={e => setEditName(e.target.value)}
                                    />
                                ) : (
                                    m.name
                                )}
                            </td>
                            <td>
                                {editId === m.id ? (
                                    <>
                                        <button onClick={() => saveEdit(m.id)}>Save</button>
                                        <button onClick={() => setEditId(null)}>Cancel</button>
                                    </>
                                ) : (
                                    <>
                                        {hasPermission('module_management_edit') && (
                                            <button onClick={() => startEdit(m)}>Edit</button>
                                        )}
                                        {hasPermission('module_management_delete') && (
                                            <button onClick={() => deleteModule(m.id)}>Delete</button>
                                        )}
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
