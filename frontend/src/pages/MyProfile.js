import { useAuth } from '../AuthContext';

export default function MyProfile() {
    const { user } = useAuth();

    if (!user) return <p>Loading profile...</p>;

    return (
        <div>
            <h1>My Profile</h1>
            <table border="1">
                <tbody>
                    <tr>
                        <th>User ID</th>
                        <td>{user.id}</td>
                    </tr>
                    <tr>
                        <th>Username</th>
                        <td>{user.username}</td>
                    </tr>
                    <tr>
                        <th>Email</th>
                        <td>{user.email}</td>
                    </tr>
                    <tr>
                        <th>Assigned Roles</th>
                        <td>{user.roles?.length > 0 ? user.roles.join(', ') : 'None'}</td>
                    </tr>
                    <tr>
                        <th>Assigned Modules</th>
                        <td>{user.modules?.map(m => m.name).join(', ') || 'None'}</td>
                    </tr>
                    <tr>
                        <th>Direct/Inherited Permissions</th>
                        <td>
                            <ul>
                                {user.permissions?.map(p => (
                                    <li key={p}>{p}</li>
                                ))}
                            </ul>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    );
}
