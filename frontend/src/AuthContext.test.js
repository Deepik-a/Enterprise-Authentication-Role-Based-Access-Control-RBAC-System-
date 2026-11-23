import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { AuthProvider, useAuth } from './AuthContext';

const mockGet = jest.fn();
const mockPost = jest.fn();
const mockRefresh = jest.fn();

jest.mock('./api', () => ({
    __esModule: true,
    default: {
        get: (...args) => mockGet(...args),
        post: (...args) => mockPost(...args),
    },
    refreshAccessToken: (...args) => mockRefresh(...args),
    setAccessToken: jest.fn(),
}));

function AuthStateProbe() {
    const { user, hasPermission } = useAuth();
    if (!user) return <p>Loading profile</p>;
    return <div>
        <p data-testid="roles">{user.roles.join(',')}</p>
        <p data-testid="orders-permission">{String(hasPermission('orders_view'))}</p>
        <p data-testid="admin-permission">{String(hasPermission('role_management_view'))}</p>
    </div>;
}

describe('AuthProvider', () => {
    beforeEach(() => {
        mockGet.mockReset().mockResolvedValue({ data: {
            email: 'manager@example.test',
            roles: ['Manager'],
            permissions: ['orders_view'],
            modules: [{ slug: 'orders', name: 'Orders', route: '/orders', order: 60 }],
            is_super_admin: false,
        } });
        mockPost.mockReset();
        mockRefresh.mockReset().mockResolvedValue('access-token');
    });

    test('loads roles and permissions from the profile API without role-based permission mapping', async () => {
        render(<AuthProvider><AuthStateProbe /></AuthProvider>);
        expect(await screen.findByTestId('roles')).toHaveTextContent('Manager');
        expect(screen.getByTestId('orders-permission')).toHaveTextContent('true');
        expect(screen.getByTestId('admin-permission')).toHaveTextContent('false');
        expect(mockRefresh).toHaveBeenCalledTimes(1);
        expect(mockGet).toHaveBeenCalledWith('auth/me/');
    });
});
