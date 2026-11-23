import { render, screen, within } from '@testing-library/react';
import '@testing-library/jest-dom';
import Sidebar from './Sidebar';
import { useAuth } from '../AuthContext';

jest.mock('../AuthContext', () => ({ useAuth: jest.fn() }));
jest.mock('react-router-dom', () => ({
    NavLink: ({ children, to }) => <a href={to}>{children}</a>,
    useNavigate: () => jest.fn(),
}));

describe('Sidebar', () => {
    test('renders and orders backend-provided modules dynamically', () => {
        useAuth.mockReturnValue({
            user: {
                email: 'manager@example.test',
                roles: ['Manager'],
                modules: [
                    { id: 9, name: 'Audit Logs', route: '/audit-logs', order: 80 },
                    { id: 2, name: 'Orders', route: '/orders', order: 60 },
                    { id: 10, name: 'No Route', route: '', order: 90 },
                ],
            },
            logout: jest.fn(),
        });
        render(<Sidebar />);
        const nav = screen.getByRole('navigation');
        const links = within(nav).getAllByRole('link').map(link => link.textContent);
        expect(links).toEqual(['Dashboard', 'Orders', 'Audit Logs', 'My Profile', 'Change Password']);
        expect(within(nav).queryByText('No Route')).not.toBeInTheDocument();
    });
});
