import { useState, useEffect } from 'react';
import api, { errorMessage } from '../api';
import { useAuth } from '../AuthContext';

export default function Roles() {
    const [roles, setRoles] = useState([]);
    const [users, setUsers] = useState([]);
    const [allPermissions, setAllPermissions] = useState([]);
    const [newRoleName, setNewRoleName] = useState('');
    const [selectedRole, setSelectedRole] = useState(null);
    const [selectedPermIds, setSelectedPermIds] = useState([]);
    const [viewUsersRole, setViewUsersRole] = useState(null);
    const [editRole, setEditRole] = useState(null);
    const { hasPermission } = useAuth();

    const fetchRoles = async () => {
        try {
            const res = await api.get('roles/');
            setRoles(res.data.results || res.data || []);
        } catch (err) {
            console.error('Failed to fetch roles', err);
        }
    };

    const fetchPermissions = async () => {
        try {
            const res = await api.get('permissions/');
            setAllPermissions(res.data.results || res.data || []);
        } catch (err) {
            console.error('Failed to fetch permissions', err);
        }
    };

    const fetchUsers = async () => {
        try {
            const res = await api.get('users/');
            setUsers(res.data.results || res.data || []);
        } catch (err) {
            console.error('Failed to fetch users', err);
        }
    };

    useEffect(() => {
        fetchRoles();
        fetchPermissions();
        fetchUsers();
    }, []);

    const createRole = async (e) => {
        e.preventDefault();
        try {
            await api.post('roles/', { name: newRoleName });
            setNewRoleName('');
            fetchRoles();
        } catch (err) {
            alert(errorMessage(err, 'Failed to create role'));
        }
    };

    const deleteRole = async (id) => {
        if (!window.confirm('Are you sure you want to delete this role?')) return;
        try {
            await api.delete(`roles/${id}/`);
            fetchRoles();
        } catch (err) {
            alert(errorMessage(err, 'Failed to delete role'));
        }
    };

    const openAssignPermissions = (role) => {
        setSelectedRole(role);
        setSelectedPermIds(role.permissions?.map(p => p.id) || []);
    };

    const togglePerm = (id) => {
        setSelectedPermIds(prev =>
            prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
        );
    };

    const savePermissions = async () => {
        try {
            await api.post(`roles/${selectedRole.id}/assign_permissions/`, {
                permission_ids: selectedPermIds,
            });
            alert('Permissions updated for role');
            setSelectedRole(null);
            fetchRoles();
        } catch (err) {
            alert(errorMessage(err, 'Failed to update permissions'));
        }
    };

    const saveEditRole = async (e) => {
        e.preventDefault();
        try {
            await api.patch(`roles/${editRole.id}/`, {
                name: editRole.name,
                is_active: editRole.is_active,
            });
            setEditRole(null);
            fetchRoles();
        } catch (err) {
            alert(errorMessage(err, 'Failed to update role'));
        }
    };

    const getUsersForRole = (roleName) => {
        return users.filter(u => u.roles?.includes(roleName));
    };

    return (
        <div>
            <h1>Role Management</h1>

            {hasPermission('role_management_create') && (
                <form onSubmit={createRole} style={{ marginBottom: 15 }}>
                    <input
                        value={newRoleName}
                        onChange={e => setNewRoleName(e.target.value)}
                        placeholder="New role name"
                        required
                    />
                    <button type="submit">Create Role</button>
                </form>
            )}

            {editRole && (
                <form onSubmit={saveEditRole} style={{ margin: '15px 0', border: '1px solid black', padding: 10 }}>
                    <h3>Edit Role: {editRole.name}</h3>
                    <div>
                        <label>Name: </label>
                        <input
                            value={editRole.name}
                            onChange={e => setEditRole({ ...editRole, name: e.target.value })}
                            required
                        />
                    </div>
                    <div>
                        <label>
                            <input
                                type="checkbox"
                                checked={editRole.is_active}
                                onChange={e => setEditRole({ ...editRole, is_active: e.target.checked })}
                            />
                            Active
                        </label>
                    </div>
                    <button type="submit">Save</button>
                    <button type="button" onClick={() => setEditRole(null)}>Cancel</button>
                </form>
            )}

            {selectedRole && (
                <div style={{ margin: '15px 0', border: '1px solid black', padding: 10 }}>
                    <h3>Assign Permissions to Role: {selectedRole.name}</h3>
                    {allPermissions.map(p => (
                        <label key={p.id} style={{ display: 'block' }}>
                            <input
                                type="checkbox"
                                checked={selectedPermIds.includes(p.id)}
                                onChange={() => togglePerm(p.id)}
                            />
                            [{p.module_name || 'Module ' + p.module}] {p.action} ({p.codename})
                        </label>
                    ))}
                    <button onClick={savePermissions} style={{ marginTop: 10 }}>Save Permissions</button>
                    <button onClick={() => setSelectedRole(null)} style={{ marginLeft: 5 }}>Cancel</button>
                </div>
            )}

            {viewUsersRole && (
                <div style={{ margin: '15px 0', border: '1px solid black', padding: 10 }}>
                    <h3>Users with Role: {viewUsersRole.name}</h3>
                    {getUsersForRole(viewUsersRole.name).length === 0 ? (
                        <p>No users assigned to this role.</p>
                    ) : (
                        <ul>
                            {getUsersForRole(viewUsersRole.name).map(u => (
                                <li key={u.id}>{u.username} ({u.email})</li>
                            ))}
                        </ul>
                    )}
                    <button onClick={() => setViewUsersRole(null)}>Close</button>
                </div>
            )}

            <table border="1">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Active</th>
                        <th>Assigned Users</th>
                        <th>Permissions</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {roles.map(r => (
                        <tr key={r.id}>
                            <td>{r.id}</td>
                            <td>{r.name}</td>
                            <td>{r.is_active ? 'Yes' : 'No'}</td>
                            <td>
                                <button onClick={() => setViewUsersRole(r)}>
                                    View Users ({getUsersForRole(r.name).length})
                                </button>
                            </td>
                            <td>
                                {r.permissions?.length > 0
                                    ? r.permissions.map(p => p.codename).join(', ')
                                    : 'No permissions'}
                            </td>
                            <td>
                                {hasPermission('role_management_edit') && !r.is_system && (
                                    <>
                                        <button onClick={() => setEditRole(r)}>Edit</button>
                                        <button onClick={() => openAssignPermissions(r)}>Assign Permissions</button>
                                    </>
                                )}
                                {hasPermission('role_management_delete') && !r.is_system && (
                                    <button onClick={() => deleteRole(r.id)}>Delete</button>
                                )}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
