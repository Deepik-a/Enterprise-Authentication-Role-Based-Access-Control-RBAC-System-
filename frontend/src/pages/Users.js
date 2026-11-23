import { useState, useEffect, useCallback } from 'react';
import api, { errorMessage } from '../api';
import { useAuth } from '../AuthContext';
import { useSweetAlert } from '../components/SweetAlert';

export default function Users() {
    const [users, setUsers] = useState([]);
    const [allRoles, setAllRoles] = useState([]);
    const [totalCount, setTotalCount] = useState(0);
    const [currentPage, setCurrentPage] = useState(1);
    const pageSize = 10;


    const [searchTerm, setSearchTerm] = useState('');
    const [searchQuery, setSearchQuery] = useState('');
    const [statusFilter, setStatusFilter] = useState('');
    const [roleFilter, setRoleFilter] = useState('');


    const [showCreate, setShowCreate] = useState(false);
    const [newUser, setNewUser] = useState({
        email: '',
        username: '',
        password: '',
        role_ids: []
    });
    const [createOtp, setCreateOtp] = useState('');
    const [awaitingOtp, setAwaitingOtp] = useState(false);
    const [showNewPassword, setShowNewPassword] = useState(false);
    const createErrors = {
        email: newUser.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(newUser.email) ? 'Enter a valid email address.' : '',
        username: newUser.username.trim().length < 3 ? 'Username must be at least 3 characters.' : '',
        password: newUser.password.length < 8 ? 'Password must be at least 8 characters.' : '',
    };
    const { alert, confirm } = useSweetAlert();

    const [viewUser, setViewUser] = useState(null);
    const [editUser, setEditUser] = useState(null);
    const [roleAssignUser, setRoleAssignUser] = useState(null);
    const [selectedRoleIds, setSelectedRoleIds] = useState([]);

    const { hasPermission, hasAnyPermission } = useAuth();


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


    const handleViewDetails = async (id) => {
        try {
            const res = await api.get(`users/${id}/`);
            setViewUser(res.data);
        } catch (err) {
            await alert('Could not load user', errorMessage(err, 'Failed to load user details'));
        }
    };


    const handleCreateUser = async (e) => {
        e.preventDefault();
        try {
            const res = await api.post('users/register_with_otp/', {
                email: newUser.email,
                username: newUser.username,
                password: newUser.password,
                role_ids: newUser.role_ids.filter(id => allRoles.find(r => r.id === id)?.code !== 'super_admin'),
            });
            setAwaitingOtp(true);
            await alert('Verification email sent', res.data.message);
        } catch (err) {
            await alert('Could not start registration', errorMessage(err));
        }
    };

    const handleVerifyCreate = async (e) => {
        e.preventDefault();
        try {
            const res = await api.post('auth/verify-otp/', { email: newUser.email, otp: createOtp });
            await alert('User created', res.data.message);
            setShowCreate(false);
            setAwaitingOtp(false);
            setCreateOtp('');
            setNewUser({ email: '', username: '', password: '', role_ids: [] });
            fetchUsers();
        } catch (err) {
            await alert('Could not verify email', errorMessage(err));
        }
    };


    const handleSaveEdit = async (e) => {
        e.preventDefault();
        try {
            await api.patch(`users/${editUser.id}/`, {
                username: editUser.username,
            });
            await alert('User updated', 'Username was updated successfully.');
            setEditUser(null);
            fetchUsers();
            if (viewUser && viewUser.id === editUser.id) {
                handleViewDetails(editUser.id);
            }
        } catch (err) {
            await alert('Could not update user', errorMessage(err));
        }
    };


    const handleToggleActive = async (id) => {
        try {
            const res = await api.post(`users/${id}/toggle_active/`);
            await alert('User status updated', `Account is now ${res.data.is_active ? 'active' : 'deactivated'}.`);
            fetchUsers();
            if (viewUser && viewUser.id === id) {
                setViewUser({ ...viewUser, is_active: res.data.is_active });
            }
        } catch (err) {
            await alert('Could not update user status', errorMessage(err, 'Failed to change user active status'));
        }
    };


    const openRoleAssignment = (u) => {
        fetchRoles();
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
            await alert('Roles updated', 'User roles were updated successfully.');
            setRoleAssignUser(null);
            fetchUsers();
            if (viewUser && viewUser.id === roleAssignUser.id) {
                handleViewDetails(roleAssignUser.id);
            }
        } catch (err) {
            await alert('Could not assign roles', errorMessage(err, 'Failed to assign roles'));
        }
    };


    const handleDeleteUser = async (id, email) => {
        if (!await confirm('Delete user?', `Are you sure you want to delete ${email}?`)) return;
        try {
            await api.delete(`users/${id}/`);
            await alert('User deleted', 'The user was deleted.');
            if (viewUser && viewUser.id === id) setViewUser(null);
            fetchUsers();
        } catch (err) {
            await alert('Could not delete user', err.response?.data?.error || errorMessage(err));
        }
    };

    const totalPages = Math.ceil(totalCount / pageSize) || 1;

    return (
        <div>
            <h1>User Management</h1>


            <div style={{ marginBottom: 15 }}>
                <form onSubmit={handleSearch} style={{ display: 'inline' }}>
                    <inpu
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


            {showCreate && (
                <div style={{ border: '1px solid black', padding: 15, marginBottom: 20 }}>
                    <h3>Create New User</h3>
                    {!awaitingOtp ? <form onSubmit={handleCreateUser} noValidate>
                        <div>
                            <label>Email: </label>
                            <inpu
                                type="text"
                                value={newUser.email}
                                onChange={e => setNewUser({ ...newUser, email: e.target.value })}
                            />
                            {newUser.email && createErrors.email && <span className="field-error">{createErrors.email}</span>}
                        </div>
                        <div>
                            <label>Username: </label>
                            <inpu
                                value={newUser.username}
                                onChange={e => setNewUser({ ...newUser, username: e.target.value })}
                            />
                            {newUser.username && createErrors.username && <span className="field-error">{createErrors.username}</span>}
                        </div>
                        <div>
                            <label>Password: </label>
                            <div className="password-input"><input type={showNewPassword ? 'text' : 'password'} value={newUser.password}
                                onChange={e => setNewUser({ ...newUser, password: e.target.value })} />
                                <button type="button" onClick={() => setShowNewPassword(v => !v)}>{showNewPassword ? 'Hide' : 'Show'}</button></div>
                            {newUser.password && createErrors.password && <span className="field-error">{createErrors.password}</span>}
                        </div>

                        <p><strong>Assign Initial Roles:</strong></p>
                        {allRoles.filter(r => r.code !== 'super_admin').map(r => (
                            <label key={r.id} style={{ display: 'block' }}>
                                <inpu
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
                            <button type="submit" disabled={Object.values(createErrors).some(Boolean)}>Send verification code</button>
                            <button type="button" onClick={() => setShowCreate(false)} style={{ marginLeft: 10 }}>Cancel</button>
                        </div>
                    </form> : <form onSubmit={handleVerifyCreate} noValidate>
                        <p>Enter the six-digit code sent to <strong>{newUser.email}</strong>.</p>
                        <label>Verification code<input inputMode="numeric" value={createOtp} maxLength={6}
                            onChange={e => setCreateOtp(e.target.value.replace(/\D/g, '').slice(0, 6))} /></label>
                        <button type="submit" disabled={createOtp.length !== 6}>Verify and create user</button>
                        <button type="button" onClick={async () => { try { const r = await api.post('auth/resend-otp/', { email: newUser.email }); await alert('Code sent', r.data.message); } catch (err) { await alert('Could not resend code', errorMessage(err)); } }}>Resend code</button>
                    </form>}
                </div>
            )}


            {viewUser && (
                <div style={{ border: '2px solid green', padding: 15, marginBottom: 20 }}>
                    <h3>Individual User Details (ID: {viewUser.id})</h3>
                    <table border="1">
                        <tbody>
                            <tr><th>Email</th><td>{viewUser.email}</td></tr>
                            <tr><th>Username</th><td>{viewUser.username}</td></tr>
                            <tr><th>Status</th><td>{viewUser.is_active ? 'Active' : 'Deactivated'}</td></tr>
                            <tr><th>Manager</th><td>{viewUser.manager_email || 'None'}</td></tr>
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


            {editUser && (
                <div style={{ border: '1px solid orange', padding: 15, marginBottom: 20 }}>
                    <h3>Edit User (ID: {editUser.id})</h3>
                    <form onSubmit={handleSaveEdit} noValidate>
                        <div>
                            <label>Username: </label>
                            <inpu
                                value={editUser.username}
                                onChange={e => setEditUser({ ...editUser, username: e.target.value })}
                            />
                            {editUser.username.trim().length < 3 && <span className="field-error">Username must be at least 3 characters.</span>}
                        </div>
                        <div style={{ marginTop: 10 }}>
                            <button type="submit" disabled={editUser.username.trim().length < 3}>Save Changes</button>
                            <button type="button" onClick={() => setEditUser(null)} style={{ marginLeft: 10 }}>Cancel</button>
                        </div>
                    </form>
                </div>
            )}


            {roleAssignUser && (
                <div style={{ border: '1px solid purple', padding: 15, marginBottom: 20 }}>
                    <h3>Change Roles for: {roleAssignUser.username} ({roleAssignUser.email})</h3>
                    <p>Select the roles to assign to this user:</p>
                    {allRoles.length === 0 ? (
                        <p>No roles available.</p>
                    ) : (
                        allRoles.filter(r => r.code !== 'super_admin').map(r => (
                            <label key={r.id} style={{ display: 'block', marginBottom: 5 }}>
                                <inpu
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

                                    <button onClick={() => handleViewDetails(u.id)}>View Details</button>


                                    {hasPermission('user_management_edit') && (
                                        <button onClick={() => setEditUser(u)} style={{ marginLeft: 5 }}>
                                            Edi
                                        </button>
                                    )}


                                    {hasPermission('user_management_edit') && (
                                        <button
                                            onClick={() => handleToggleActive(u.id)}
                                            style={{ marginLeft: 5 }}
                                        >
                                            {u.is_active ? 'Deactivate' : 'Activate'}
                                        </button>
                                    )}


                                    {hasAnyPermission(['user_management_assign', 'user_management_edit']) && (
                                        <button
                                            onClick={() => openRoleAssignment(u)}
                                            style={{ marginLeft: 5 }}
                                        >
                                            Assign Roles
                                        </button>
                                    )}


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
