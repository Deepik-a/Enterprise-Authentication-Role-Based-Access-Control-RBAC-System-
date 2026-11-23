
import { useEffect, useState } from 'react';
import api, { errorMessage } from '../api';
import { useAuth } from '../AuthContext';
import { useSweetAlert } from '../components/SweetAlert';

export default function Permissions() {
  const [permissions, setPermissions] = useState([]);
  const [modules, setModules] = useState([]);
  const [newPerm, setNewPerm] = useState({ module: '', action: '', codename: '' });
  const [editPerm, setEditPerm] = useState(null);
  const [filterModule, setFilterModule] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const { hasPermission } = useAuth();
  const { alert, confirm } = useSweetAlert();
  const permissionErrors = {
    module: newPerm.module ? '' : 'Select a module.',
    action: /^[a-z][a-z0-9_-]*$/i.test(newPerm.action.trim()) ? '' : 'Use letters, numbers, underscores, or hyphens.',
    codename: /^[a-z][a-z0-9_]*$/i.test(newPerm.codename.trim()) ? '' : 'Use letters, numbers, and underscores.',
  };
  const editPermissionErrors = editPerm ? {
    action: /^[a-z][a-z0-9_-]*$/i.test(editPerm.action.trim()) ? '' : 'Use letters, numbers, underscores, or hyphens.',
    codename: /^[a-z][a-z0-9_]*$/i.test(editPerm.codename.trim()) ? '' : 'Use letters, numbers, and underscores.',
  } : {};

  const fetchData = async () => {
    try {
      const [permRes, modRes] = await Promise.all([
        api.get('permissions/'),
        api.get('modules/')
      ]);
      setPermissions(permRes.data.results || permRes.data || []);
      setModules(modRes.data.results || modRes.data || []);
    } catch (err) {
      console.error('Failed to fetch permissions or modules', err);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleModuleChange = (moduleId) => {
    const selectedMod = modules.find(m => String(m.id) === String(moduleId));
    const modSlug = selectedMod ? (selectedMod.slug || selectedMod.name.toLowerCase().replace(/\s+/g, '_')) : '';
    const suggestedCodename = modSlug && newPerm.action ? `${modSlug}_${newPerm.action.toLowerCase().replace(/\s+/g, '_')}` : '';
    setNewPerm({
      ...newPerm,
      module: moduleId,
      codename: suggestedCodename || newPerm.codename
    });
  };

  const handleActionChange = (actionVal) => {
    const selectedMod = modules.find(m => String(m.id) === String(newPerm.module));
    const modSlug = selectedMod ? (selectedMod.slug || selectedMod.name.toLowerCase().replace(/\s+/g, '_')) : '';
    const suggestedCodename = modSlug && actionVal ? `${modSlug}_${actionVal.toLowerCase().replace(/\s+/g, '_')}` : '';
    setNewPerm({
      ...newPerm,
      action: actionVal,
      codename: suggestedCodename || newPerm.codename
    });
  };

  const createPermission = async (e) => {
    e.preventDefault();
    try {
      await api.post('permissions/', newPerm);
      await alert('Permission created', `Permission "${newPerm.codename}" was created successfully.`);
      setNewPerm({ module: '', action: '', codename: '' });
      fetchData();
    } catch (err) {
      const errData = err.response?.data;
      let errorMsg = 'Failed to create permission.';
      if (errData) {
        if (errData.codename) {
          errorMsg = `Codename Error: ${errData.codename.join(' ')}`;
        } else if (errData.non_field_errors) {
          errorMsg = `Conflict: ${errData.non_field_errors.join(' ')}`;
        } else if (errData.module) {
          errorMsg = `Module Error: ${errData.module.join(' ')}`;
        } else if (errData.action) {
          errorMsg = `Action Error: ${errData.action.join(' ')}`;
        } else {
          errorMsg = JSON.stringify(errData);
        }
      }
      await alert('Could not create permission', errorMsg);
    }
  };

  const deletePermission = async (id, codename) => {
    if (!await confirm('Delete permission?', `Are you sure you want to delete permission "${codename}"?`)) return;
    try {
      await api.delete(`permissions/${id}/`);
      await alert('Permission deleted', 'The permission was deleted successfully.');
      fetchData();
    } catch (err) {
      await alert('Could not delete permission', errorMessage(err, 'Failed to delete permission'));
    }
  };

  const savePermission = async (e) => {
    e.preventDefault();
    try {
      await api.patch(`permissions/${editPerm.id}/`, {
        module: Number(editPerm.module), action: editPerm.action, codename: editPerm.codename,
      });
      setEditPerm(null);
      fetchData();
    } catch (err) {
      await alert('Could not update permission', errorMessage(err, 'Failed to update permission'));
    }
  };


  const filteredPermissions = permissions.filter(p => {
    const matchMod = filterModule ? String(p.module) === String(filterModule) : true;
    const matchSearch = searchTerm
      ? p.codename?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        p.action?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (p.module_name && p.module_name.toLowerCase().includes(searchTerm.toLowerCase()))
      : true;
    return matchMod && matchSearch;
  });

  return (
    <div>
      <h1>Permission Management</h1>
      <p>Create permissions and view codenames associated with each module.</p>


      {hasPermission('permission_management_create') && (
        <form onSubmit={createPermission} noValidate style={{ marginBottom: '1.5rem', border: '1px solid black', padding: 15 }}>
          <h3>Create New Permission</h3>
          <div>
            <label>Module: </label>
            <select
              value={newPerm.module}
              onChange={e => handleModuleChange(e.target.value)}
            >
              <option value="" disabled>Select Module</option>
              {modules.map(m => (
                <option key={m.id} value={m.id}>{m.name}</option>
              ))}
            </select>
            {newPerm.module === '' && <span className="field-error">{permissionErrors.module}</span>}
          </div>

          <div style={{ marginTop: 8 }}>
            <label>Action (e.g. view, create, edit, delete, export): </label>
            <inpu
              placeholder="e.g. view, create, edit"
              value={newPerm.action}
              onChange={e => handleActionChange(e.target.value)}
            />
            {newPerm.action && permissionErrors.action && <span className="field-error">{permissionErrors.action}</span>}
          </div>

          <div style={{ marginTop: 8 }}>
            <label>Codename: </label>
            <inpu
              placeholder="e.g. dashboard_view"
              value={newPerm.codename}
              onChange={e => setNewPerm({ ...newPerm, codename: e.target.value })}
            />
            {newPerm.codename && permissionErrors.codename && <span className="field-error">{permissionErrors.codename}</span>}
            <small style={{ display: 'block', color: 'gray' }}>
              Auto-suggested: <code>&lt;module_name&gt;_&lt;action&gt;</code> (must be unique)
            </small>
          </div>

          <div style={{ marginTop: 10 }}>
            <button type="submit" disabled={Object.values(permissionErrors).some(Boolean)}>Create Permission</button>
          </div>
        </form>
      )}

      {editPerm && (
        <form onSubmit={savePermission} noValidate style={{ marginBottom: '1.5rem', border: '1px solid black', padding: 15 }}>
          <h3>Edit Permission</h3>
          <label>Module: <select value={editPerm.module}
            onChange={e => setEditPerm({ ...editPerm, module: e.target.value })}>
            {modules.filter(m => !m.is_system).map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
          </select></label>
          <label> Action: <input value={editPerm.action}
            onChange={e => setEditPerm({ ...editPerm, action: e.target.value })} /></label>
          {editPerm.action && editPermissionErrors.action && <span className="field-error">{editPermissionErrors.action}</span>}
          <label> Codename: <input value={editPerm.codename}
            onChange={e => setEditPerm({ ...editPerm, codename: e.target.value })} /></label>
          {editPerm.codename && editPermissionErrors.codename && <span className="field-error">{editPermissionErrors.codename}</span>}
          <button type="submit" disabled={Object.values(editPermissionErrors).some(Boolean)}>Save Permission</button>
          <button type="button" onClick={() => setEditPerm(null)}>Cancel</button>
        </form>
      )}


      <div style={{ marginBottom: 15 }}>
        <inpu
          placeholder="Search codename or action..."
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
        />
        <span style={{ marginLeft: 10 }}>Filter by Module: </span>
        <select
          value={filterModule}
          onChange={e => setFilterModule(e.target.value)}
        >
          <option value="">All Modules</option>
          {modules.map(m => (
            <option key={m.id} value={m.id}>{m.name}</option>
          ))}
        </select>
        {(searchTerm || filterModule) && (
          <button
            onClick={() => { setSearchTerm(''); setFilterModule(''); }}
            style={{ marginLeft: 10 }}
          >
            Clear Filters
          </button>
        )}
      </div>


      <table border="1" cellPadding="6" style={{ width: '100%' }}>
        <thead>
          <tr>
            <th>ID</th>
            <th>Module</th>
            <th>Action</th>
            <th>Codename</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {filteredPermissions.length === 0 ? (
            <tr>
              <td colSpan="5">No permissions found.</td>
            </tr>
          ) : (
            filteredPermissions.map(p => (
              <tr key={p.id}>
                <td>{p.id}</td>
                <td>{p.module_name || (modules.find(m => m.id === p.module)?.name) || p.module}</td>
                <td>{p.action}</td>
                <td><code>{p.codename}</code></td>
                <td>
                  {modules.find(m => String(m.id) === String(p.module))?.is_system ? (
                    <span>System protected</span>
                  ) : (
                    <>
                      {hasPermission('permission_management_edit') && <button onClick={() => setEditPerm({
                        id: p.id, module: String(p.module), action: p.action, codename: p.codename,
                      })}>Edit</button>}
                      {hasPermission('permission_management_delete') && (
                        <button onClick={() => deletePermission(p.id, p.codename)}>Delete</button>
                      )}
                    </>
                  )}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
