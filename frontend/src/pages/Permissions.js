// src/pages/Permissions.js
import { useEffect, useState } from 'react';
import api, { errorMessage } from '../api';
import { useAuth } from '../AuthContext';

export default function Permissions() {
  const [permissions, setPermissions] = useState([]);
  const [modules, setModules] = useState([]);
  const [newPerm, setNewPerm] = useState({ module: '', action: '', codename: '' });
  const [filterModule, setFilterModule] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const { hasPermission } = useAuth();

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
    const modSlug = selectedMod ? selectedMod.name.toLowerCase().replace(/\s+/g, '_') : '';
    const suggestedCodename = modSlug && newPerm.action ? `${modSlug}_${newPerm.action.toLowerCase().replace(/\s+/g, '_')}` : '';
    setNewPerm({
      ...newPerm,
      module: moduleId,
      codename: suggestedCodename || newPerm.codename
    });
  };

  const handleActionChange = (actionVal) => {
    const selectedMod = modules.find(m => String(m.id) === String(newPerm.module));
    const modSlug = selectedMod ? selectedMod.name.toLowerCase().replace(/\s+/g, '_') : '';
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
      alert(`Permission "${newPerm.codename}" created successfully!`);
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
      alert(errorMsg);
    }
  };

  const deletePermission = async (id, codename) => {
    if (!window.confirm(`Are you sure you want to delete permission "${codename}"?`)) return;
    try {
      await api.delete(`permissions/${id}/`);
      alert('Permission deleted successfully');
      fetchData();
    } catch (err) {
      alert(errorMessage(err, 'Failed to delete permission'));
    }
  };

  // Filter permissions
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

      {/* Create Permission Form */}
      {hasPermission('permission_management_create') && (
        <form onSubmit={createPermission} style={{ marginBottom: '1.5rem', border: '1px solid black', padding: 15 }}>
          <h3>Create New Permission</h3>
          <div>
            <label>Module: </label>
            <select
              required
              value={newPerm.module}
              onChange={e => handleModuleChange(e.target.value)}
            >
              <option value="" disabled>Select Module</option>
              {modules.map(m => (
                <option key={m.id} value={m.id}>{m.name}</option>
              ))}
            </select>
          </div>

          <div style={{ marginTop: 8 }}>
            <label>Action (e.g. view, create, edit, delete, export): </label>
            <input
              placeholder="e.g. view, create, edit"
              required
              value={newPerm.action}
              onChange={e => handleActionChange(e.target.value)}
            />
          </div>

          <div style={{ marginTop: 8 }}>
            <label>Codename: </label>
            <input
              placeholder="e.g. dashboard_view"
              required
              value={newPerm.codename}
              onChange={e => setNewPerm({ ...newPerm, codename: e.target.value })}
            />
            <small style={{ display: 'block', color: 'gray' }}>
              Auto-suggested: <code>&lt;module_name&gt;_&lt;action&gt;</code> (must be unique)
            </small>
          </div>

          <div style={{ marginTop: 10 }}>
            <button type="submit">Create Permission</button>
          </div>
        </form>
      )}

      {/* Filter and Search Bar */}
      <div style={{ marginBottom: 15 }}>
        <input
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

      {/* Permissions Table */}
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
                  <button onClick={() => deletePermission(p.id, p.codename)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
