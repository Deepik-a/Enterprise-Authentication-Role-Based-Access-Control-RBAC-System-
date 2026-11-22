import { useState, useEffect, useCallback } from 'react';
import api, { errorMessage } from '../api';
import { useAuth } from '../AuthContext';

export default function Users() {
    const [users, setUsers] = useState([]);
    const [allRoles, setAllRoles] = useState([]);
    const [totalCount, setTotalCount] = useState(0);
    const [currentPage, setCurrentPage] = useState(1);
    const pageSize = 10;

    // Search and filter states
    const [searchTerm, setSearchTerm] = useState('');
    const [searchQuery, setSearchQuery] = useState('');
    const [statusFilter, setStatusFilter] = useState('');
    const [roleFilter, setRoleFilter] = useState('');

    // Modal / Panel states
    const [showCreate, setShowCreate] = useState(false);
    const [newUser, setNewUser] = useState({
        email: '',
        username: '',
        password: '',
        first_name: '',
        last_name: '',
        role_ids: []
    });

    const [viewUser, setViewUser] = useState(null);
    const [editUser, setEditUser] = useState(null);
    const [roleAssignUser, setRoleAssignUser] = useState(null);
    const [selectedRoleIds, setSelectedRoleIds] = useState([]);

    const { hasPermission } = useAuth();

    // Fetch user list with search, filter, and pagination
    const fetchUsers = useCallback(async () => {
        try {
            const params = new URLSearchParams();
            params.append('page', currentPage);
            if (searchQuery) params.append('search', searchQuery);
            if (statusFilter !== '') params.append('is_active', statusFilter);
            if (roleFilter !== '') params.append('roles', roleFilter);

            const res = await api.get(`users/?${params.toString()}`);
            if (res.data.results) {
                setUsers(res.data.results);
                setTotalCount(res.data.count || 0);
            } else {
                setUsers(res.data || []);
                setTotalCount(res.data?.length || 0);
            }
        } catch (err) {
            console.error('Failed to fetch users', err);
        }
    }, [currentPage, searchQuery, statusFilter, roleFilter]);

    // Fetch all roles for dropdowns and role assignment
    const fetchRoles = async () => {
        try {
            const res = await api.get('roles/');
            setAllRoles(res.data.results || res.data || []);
        } catch (err) {
            console.error('Failed to fetch roles', err);
        }
    };

    useEffect(() => {
        fetchRoles();
    }, []);

    useEffect(() => {
        fetchUsers();
    }, [fetchUsers]);

    // Search handler
    const handleSearch = (e) => {
        e.preventDefault();
        setCurrentPage(1);
        setSearchQuery(searchTerm);
    };

    const handleResetSearch = () => {
        setSearchTerm('');
        setSearchQuery('');
        setStatusFilter('');
        setRoleFilter('');
        setCurrentPage(1);
    };

    // View individual user details
    const handleViewDetails = async (id) => {
        try {
            const res = await api.get(`users/${id}/`);
            setViewUser(res.data);
        } catch (err) {
            alert(errorMessage(err, 'Failed to load user details'));
        }
    };

    // Create user
    const handleCreateUser = async (e) => {
        e.preventDefault();
        try {
            const res = await api.post('users/', {
                email: newUser.email,
                username: newUser.username,
                password: newUser.password,
                first_name: newUser.first_name,
                last_name: newUser.last_name,
            });

            // If roles were selected during creation, assign them
            if (newUser.role_ids.length > 0 && res.data?.id) {
                await api.post(`users/${res.data.id}/assign_roles/`, {
                    role_ids: newUser.role_ids,
                });
            }

            alert('User created successfully');
            setShowCreate(false);
            setNewUser({
                email: '',
                username: '',
                password: '',
                first_name: '',
                last_name: '',
                role_ids: []
            });
            fetchUsers();
        } catch (err) {
            alert('Failed to create user: ' + errorMessage(err));
        }
    };

    // Edit user details
    const handleSaveEdit = async (e) => {
        e.preventDefault();
        try {
            await api.patch(`users/${editUser.id}/`, {
                username: editUser.username,
                email: editUser.email,
                first_name: editUser.first_name,
                last_name: editUser.last_name,
                manager: editUser.manager || null,
            });
            alert('User updated successfully');
            setEditUser(null);
            fetchUsers();
            if (viewUser && viewUser.id === editUser.id) {
                handleViewDetails(editUser.id);
            }
        } catch (err) {
            alert('Failed to update user: ' + errorMessage(err));
        }
    };

    // Toggle active / deactivate
    const handleToggleActive = async (id) => {
        try {
            const res = await api.post(`users/${id}/toggle_active/`);
            alert(`User status changed to: ${res.data.is_active ? 'Active' : 'Deactivated'}`);
            fetchUsers();
            if (viewUser && viewUser.id === id) {
                setViewUser({ ...viewUser, is_active: res.data.is_active });
            }
        } catch (err) {
            alert(errorMessage(err, 'Failed to change user active status'));
        }
    };

    // Assign / Change roles
    const openRoleAssignment = (u) => {
        setRoleAssignUser(u);
        const currentRoleIds = allRoles
            .filter(r => u.roles?.includes(r.name))
            .map(r => r.id);
        setSelectedRoleIds(currentRoleIds);
    };

    const toggleRoleId = (id) => {
        setSelectedRoleIds(prev =>
            prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
        );
    };

    const handleSaveRoles = async () => {
        try {
            await api.post(`users/${roleAssignUser.id}/assign_roles/`, {
                role_ids: selectedRoleIds,
            });
            alert('User roles updated successfully');
            setRoleAssignUser(null);
            fetchUsers();
            if (viewUser && viewUser.id === roleAssignUser.id) {
                handleViewDetails(roleAssignUser.id);
            }
        } catch (err) {
            alert(errorMessage(err, 'Failed to assign roles'));
        }
    };

    // Delete user
    const handleDeleteUser = async (id, email) => {
        if (!window.confirm(`Are you sure you want to delete user "${email}"?`)) return;
        try {
            await api.delete(`users/${id}/`);
            alert('User deleted');
            if (viewUser && viewUser.id === id) setViewUser(null);
            fetchUsers();
        } catch (err) {
            alert(err.response?.data?.error || 'Failed to delete user: ' + JSON.stringify(err.response?.data || err.message));
        }
    };

    const totalPages = Math.ceil(totalCount / pageSize) || 1;

    return (
        <div>
            <h1>User Management</h1>

            {/* Top Toolbar: Search, Filter & Create */}
            <div style={{ marginBottom: 15 }}>
                <form onSubmit={handleSearch} style={{ display: 'inline' }}>
                    <input
                        placeholder="Search email, username, name..."
                        value={searchTerm}
                        onChange={e => setSearchTerm(e.target.value)}
                    />
                    <button type="submit">Search</button>
                </form>

                <span style={{ marginLeft: 10 }}>Filter Status: </span>
                <select
                    value={statusFilter}
                    onChange={e => {
                        setStatusFilter(e.target.value);
                        setCurrentPage(1);
                    }}
                >
                    <option value="">All Statuses</option>
                    <option value="true">Active Only</option>
                    <option value="false">Deactivated Only</option>
                </select>

                <span style={{ marginLeft: 10 }}>Filter Role: </span>
                <select
                    value={roleFilter}
                    onChange={e => {
                        setRoleFilter(e.target.value);
                        setCurrentPage(1);
                    }}
                >
                    <option value="">All Roles</option>
                    {allRoles.map(r => (
                        <option key={r.id} value={r.id}>{r.name}</option>
                    ))}
                </select>

                <button onClick={handleResetSearch} style={{ marginLeft: 10 }}>Reset Filters</button>

                {hasPermission('user_management_create') && (
                    <button
                        onClick={() => setShowCreate(!showCreate)}
                        style={{ marginLeft: 15 }}
                    >
                        {showCreate ? 'Close Form' : '+ Create User'}
                    </button>
                )}
            </div>

            {/* Create User Form */}
            {showCreate && (
                <div style={{ border: '1px solid black', padding: 15, marginBottom: 20 }}>
                    <h3>Create New User</h3>
                    <form onSubmit={handleCreateUser}>
                        <div>
                            <label>Email: </label>
                            <input
                                type="email"
                                required
                                value={newUser.email}
                                onChange={e => setNewUser({ ...newUser, email: e.target.value })}
                            />
                        </div>
                        <div>
                            <label>Username: </label>
                            <input
                                required
                                value={newUser.username}
                                onChange={e => setNewUser({ ...newUser, username: e.target.value })}
                            />
                        </div>
                        <div>
                            <label>Password: </label>
                            <input
                                type="password"
                                required
                                minLength={8}
                                value={newUser.password}
                                onChange={e => setNewUser({ ...newUser, password: e.target.value })}
                            />
                        </div>
                        <div>
                            <label>First Name: </label>
                            <input
                                value={newUser.first_name}
                                onChange={e => setNewUser({ ...newUser, first_name: e.target.value })}
                            />
                        </div>
                        <div>
                            <label>Last Name: </label>
                            <input
                                value={newUser.last_name}
                                onChange={e => setNewUser({ ...newUser, last_name: e.target.value })}
                            />
                        </div>

                        <p><strong>Assign Initial Roles:</strong></p>
                        {allRoles.map(r => (
                            <label key={r.id} style={{ display: 'block' }}>
                                <input
                                    type="checkbox"
                                    checked={newUser.role_ids.includes(r.id)}
                                    onChange={() => {
                                        const ids = newUser.role_ids.includes(r.id)
                                            ? newUser.role_ids.filter(x => x !== r.id)
                                            : [...newUser.role_ids, r.id];
                                        setNewUser({ ...newUser, role_ids: ids });
                                    }}
                                />
                                {r.name}
                            </label>
                        ))}

                        <div style={{ marginTop: 10 }}>
                            <button type="submit">Submit & Create User</button>
                            <button type="button" onClick={() => setShowCreate(false)} style={{ marginLeft: 10 }}>Cancel</button>
                        </div>
                    </form>
                </div>
            )}

            {/* Individual User Details Viewer */}
            {viewUser && (
                <div style={{ border: '2px solid green', padding: 15, marginBottom: 20 }}>
                    <h3>Individual User Details (ID: {viewUser.id})</h3>
                    <table border="1">
                        <tbody>
                            <tr><th>Email</th><td>{viewUser.email}</td></tr>
                            <tr><th>Username</th><td>{viewUser.username}</td></tr>
                            <tr><th>First Name</th><td>{viewUser.first_name || '-'}</td></tr>
                            <tr><th>Last Name</th><td>{viewUser.last_name || '-'}</td></tr>
                            <tr><th>Status</th><td>{viewUser.is_active ? 'Active' : 'Deactivated'}</td></tr>
                            <tr><th>Manager</th><td>{viewUser.manager_email || 'None'}</td></tr>
                            <tr><th>Superuser?</th><td>{viewUser.is_superuser ? 'Yes' : 'No'}</td></tr>
                            <tr><th>Roles</th><td>{viewUser.roles?.length > 0 ? viewUser.roles.join(', ') : 'None'}</td></tr>
                            <tr><th>Date Joined</th><td>{viewUser.date_joined ? new Date(viewUser.date_joined).toLocaleString() : '-'}</td></tr>
                            <tr><th>Last Login</th><td>{viewUser.last_login ? new Date(viewUser.last_login).toLocaleString() : 'Never'}</td></tr>
                        </tbody>
                    </table>
                    <div style={{ marginTop: 10 }}>
                        <button onClick={() => setViewUser(null)}>Close Details</button>
                    </div>
                </div>
            )}

            {/* Update / Edit User Form */}
            {editUser && (
                <div style={{ border: '1px solid orange', padding: 15, marginBottom: 20 }}>
                    <h3>Edit User (ID: {editUser.id})</h3>
                    <form onSubmit={handleSaveEdit}>
                        <div>
                            <label>Email: </label>
                            <input
                                type="email"
                                required
                                value={editUser.email}
                                onChange={e => setEditUser({ ...editUser, email: e.target.value })}
                            />
                        </div>
                        <div>
                            <label>Username: </label>
                            <input
                                required
                                value={editUser.username}
                                onChange={e => setEditUser({ ...editUser, username: e.target.value })}
                            />
                        </div>
                        <div>
                            <label>First Name: </label>
                            <input
                                value={editUser.first_name || ''}
                                onChange={e => setEditUser({ ...editUser, first_name: e.target.value })}
                            />
                        </div>
                        <div>
                            <label>Last Name: </label>
                            <input
                                value={editUser.last_name || ''}
                                onChange={e => setEditUser({ ...editUser, last_name: e.target.value })}
                            />
                        </div>
                        <div>
                            <label>Manager (team): </label>
                            <select
                                value={editUser.manager || ''}
                                onChange={e => setEditUser({ ...editUser, manager: e.target.value ? Number(e.target.value) : null })}
                            >
                                <option value="">No manager</option>
                                {users.filter(u => u.id !== editUser.id).map(u => (
                                    <option key={u.id} value={u.id}>{u.email}</option>
                                ))}
                            </select>
                        </div>
                        <div style={{ marginTop: 10 }}>
                            <button type="submit">Save Changes</button>
                            <button type="button" onClick={() => setEditUser(null)} style={{ marginLeft: 10 }}>Cancel</button>
                        </div>
                    </form>
                </div>
            )}

            {/* Assign / Change Roles Panel */}
            {roleAssignUser && (
                <div style={{ border: '1px solid purple', padding: 15, marginBottom: 20 }}>
                    <h3>Change Roles for: {roleAssignUser.username} ({roleAssignUser.email})</h3>
                    <p>Select the roles to assign to this user:</p>
                    {allRoles.length === 0 ? (
                        <p>No roles available.</p>
                    ) : (
                        allRoles.map(r => (
                            <label key={r.id} style={{ display: 'block', marginBottom: 5 }}>
                                <input
                                    type="checkbox"
                                    checked={selectedRoleIds.includes(r.id)}
                                    onChange={() => toggleRoleId(r.id)}
                                />
                                <strong>{r.name}</strong> {r.is_active ? '' : '(Inactive Role)'}
                            </label>
                        ))
                    )}
                    <div style={{ marginTop: 10 }}>
                        <button onClick={handleSaveRoles}>Save Roles</button>
                        <button onClick={() => setRoleAssignUser(null)} style={{ marginLeft: 10 }}>Cancel</button>
                    </div>
                </div>
            )}

            {/* Main Users Table */}
            <table border="1" cellPadding="5" style={{ width: '100%', marginTop: 10 }}>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Email</th>
                        <th>Username</th>
                        <th>Status</th>
                        <th>Assigned Roles</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {users.length === 0 ? (
                        <tr>
                            <td colSpan="6">No users found matching current filters.</td>
                        </tr>
                    ) : (
                        users.map(u => (
                            <tr key={u.id}>
                                <td>{u.id}</td>
                                <td>{u.email}</td>
                                <td>{u.username}</td>
                                <td>
                                    <strong>{u.is_active ? 'Active' : 'Deactivated'}</strong>
                                </td>
                                <td>{u.roles?.length > 0 ? u.roles.join(', ') : 'None'}</td>
                                <td>
                                    {/* View individual details */}
                                    <button onClick={() => handleViewDetails(u.id)}>View Details</button>

                                    {/* Update User */}
                                    {hasPermission('user_management_edit') && (
                                        <button onClick={() => setEditUser(u)} style={{ marginLeft: 5 }}>
                                            Edit
                                        </button>
                                    )}

                                    {/* Activate / Deactivate */}
                                    {hasPermission('user_management_edit') && (
                                        <button
                                            onClick={() => handleToggleActive(u.id)}
                                            style={{ marginLeft: 5 }}
                                        >
                                            {u.is_active ? 'Deactivate' : 'Activate'}
                                        </button>
                                    )}

                                    {/* Assign / Change Roles */}
                                    {hasPermission('user_management_edit') && (
                                        <button
                                            onClick={() => openRoleAssignment(u)}
                                            style={{ marginLeft: 5 }}
                                        >
                                            Assign Roles
                                        </button>
                                    )}

                                    {/* Delete User */}
                                    {hasPermission('user_management_delete') && (
                                        <button
                                            onClick={() => handleDeleteUser(u.id, u.email)}
                                            style={{ marginLeft: 5 }}
                                        >
                                            Delete
                                        </button>
                                    )}
                                </td>
                            </tr>
                        ))
                    )}
                </tbody>
            </table>

            {/* Pagination Controls */}
            <div style={{ marginTop: 15 }}>
                <button
                    disabled={currentPage <= 1}
                    onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                >
                    &laquo; Previous
                </button>

                <span style={{ margin: '0 15px' }}>
                    Page <strong>{currentPage}</strong> of <strong>{totalPages}</strong> (Total Users: {totalCount})
                </span>

                <button
                    disabled={currentPage >= totalPages}
                    onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                >
                    Next &raquo;
                </button>
            </div>
        </div>
    );
}
