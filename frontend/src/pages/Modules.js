import { useCallback, useEffect, useState } from 'react';
import api, { errorMessage } from '../api';
import { useAuth } from '../AuthContext';
import { useSweetAlert } from '../components/SweetAlert';

const CODE_NAME_PATTERN = /^[a-z][a-z0-9_]*$/;

export default function Modules() {
    const [modules, setModules] = useState([]);
    const [form, setForm] = useState({ name: '', codeName: '' });
    const [editModule, setEditModule] = useState(null);
    const { hasPermission } = useAuth();
    const { alert, confirm } = useSweetAlert();

    const fetchModules = useCallback(async () => {
        try {
            const response = await api.get('modules/');
            setModules(response.data.results || response.data);
        } catch (err) {
            await alert('Could not load modules', errorMessage(err, 'Failed to fetch modules'));
        }
    }, [alert]);

    useEffect(() => {
        fetchModules();
    }, [fetchModules]);

    const validate = (value, currentId = null) => {
        const errors = {};
        if (!value.name.trim()) errors.name = 'Module name is required.';
        const codeName = (value.codeName ?? value.slug ?? '').trim();
        if (!codeName) errors.codeName = 'Code name is required.';
        else if (!CODE_NAME_PATTERN.test(codeName)) errors.codeName = 'Use lowercase letters, numbers, and underscores; start with a letter.';
        else if (modules.some(module => module.id !== currentId && module.slug === codeName)) errors.codeName = 'This code name is already in use.';
        return errors;
    };

    const createErrors = validate(form);
    const editErrors = editModule ? validate(editModule, editModule.id) : {};

    const createModule = async (event) => {
        event.preventDefault();
        if (Object.keys(createErrors).length) return;
        try {
            await api.post('modules/', { name: form.name.trim(), slug: form.codeName.trim() });
            setForm({ name: '', codeName: '' });
            await fetchModules();
        } catch (err) {
            await alert('Could not create module', errorMessage(err, 'Failed to create module'));
        }
    };

    const saveEdit = async (event) => {
        event.preventDefault();
        if (Object.keys(editErrors).length) return;
        try {
            await api.patch(`modules/${editModule.id}/`, {
                name: editModule.name.trim(),
                slug: editModule.slug.trim(),
            });
            setEditModule(null);
            await fetchModules();
        } catch (err) {
            await alert('Could not update module', errorMessage(err, 'Failed to update module'));
        }
    };

    const deleteModule = async (module) => {
        if (module.is_system) return;
        if (!await confirm('Delete module?', `Delete ${module.name} and its permissions?`)) return;
        try {
            await api.delete(`modules/${module.id}/`);
            await fetchModules();
        } catch (err) {
            await alert('Could not delete module', errorMessage(err, 'Failed to delete module'));
        }
    };

    return (
        <div>
            <h1>Module Management</h1>
            {hasPermission('module_management_create') && (
                <form className="module-form" onSubmit={createModule} noValidate>
                    <label>Module Name
                        <input value={form.name} onChange={event => setForm({ ...form, name: event.target.value })} />
                        {createErrors.name && <span className="field-error">{createErrors.name}</span>}
                    </label>
                    <label>Code Name
                        <input value={form.codeName} onChange={event => setForm({ ...form, codeName: event.target.value })} />
                        {createErrors.codeName && <span className="field-error">{createErrors.codeName}</span>}
                    </label>
                    <button className="btn" type="submit" disabled={Object.keys(createErrors).length > 0}>Add Module</button>
                </form>
            )}

            <table>
                <thead>
                    <tr><th>ID</th><th>Module Name</th><th>Code Name</th><th>Actions</th></tr>
                </thead>
                <tbody>
                    {modules.map(module => (
                        <tr key={module.id}>
                            <td>{module.id}</td>
                            <td>
                                {editModule?.id === module.id ? (
                                    <label className="module-edit-field">Module Name
                                        <input value={editModule.name} onChange={event => setEditModule({ ...editModule, name: event.target.value })} />
                                        {editErrors.name && <span className="field-error">{editErrors.name}</span>}
                                    </label>
                                ) : module.name}
                            </td>
                            <td>
                                {editModule?.id === module.id ? (
                                    <label className="module-edit-field">Code Name
                                        <input value={editModule.slug || ''} disabled={module.is_system}
                                            onChange={event => setEditModule({ ...editModule, slug: event.target.value })} />
                                        {editErrors.codeName && <span className="field-error">{editErrors.codeName}</span>}
                                    </label>
                                ) : module.slug || '—'}
                            </td>
                            <td className="module-actions">
                                {editModule?.id === module.id ? (
                                    <>
                                        <button className="btn" onClick={saveEdit} disabled={Object.keys(editErrors).length > 0}>Save</button>
                                        <button type="button" onClick={() => setEditModule(null)}>Cancel</button>
                                    </>
                                ) : (
                                    <>
                                        {hasPermission('module_management_edit') && <button onClick={() => setEditModule({ ...module, codeName: module.slug || '' })}>Edit</button>}
                                        {hasPermission('module_management_delete') && (module.is_system ? (
                                            <span className="muted">System protected</span>
                                        ) : <button className="btn-danger" onClick={() => deleteModule(module)}>Delete</button>)}
                                    </>
                                )}
                            </td>
                        </tr>
                    ))}
                    {modules.length === 0 && <tr><td colSpan="4">No modules found.</td></tr>}
                </tbody>
            </table>
        </div>
    );
}
