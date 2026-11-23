import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import ProtectedRoute from './ProtectedRoute';
import { useAuth } from '../AuthContext';

jest.mock('../AuthContext', () => ({ useAuth: jest.fn() }));
jest.mock('react-router-dom', () => ({
    Link: ({ children, to }) => <a href={to}>{children}</a>,
    Navigate: ({ to }) => <div data-testid="redirect">{to}</div>,
    useLocation: () => ({ pathname: '/private' }),
}));

function renderProtectedRoute() {
    return render(<ProtectedRoute requiredPermission="reports_view"><p>Private report</p></ProtectedRoute>);
}

describe('ProtectedRoute', () => {
    test('redirects unauthenticated users to login', () => {
        useAuth.mockReturnValue({ user: null, loading: false, hasPermission: () => false });
        renderProtectedRoute();
        expect(screen.getByTestId('redirect')).toHaveTextContent('/login');
        expect(screen.queryByText('Private report')).not.toBeInTheDocument();
    });

    test('blocks a direct URL when the user lacks its permission', () => {
        useAuth.mockReturnValue({ user: { id: 1 }, loading: false, hasPermission: () => false });
        renderProtectedRoute();
        expect(screen.getByText(/Access denied/)).toBeInTheDocument();
        expect(screen.queryByText('Private report')).not.toBeInTheDocument();
    });

    test('renders the route when the user has its permission', () => {
        useAuth.mockReturnValue({ user: { id: 1 }, loading: false, hasPermission: () => true });
        renderProtectedRoute();
        expect(screen.getByText('Private report')).toBeInTheDocument();
    });
});
