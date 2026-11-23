import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import Products from './Products';
import { useAuth } from '../AuthContext';
import api from '../api';
import { SweetAlertProvider } from '../components/SweetAlert';

jest.mock('../AuthContext', () => ({ useAuth: jest.fn() }));
jest.mock('../api', () => ({
    __esModule: true,
    default: { get: jest.fn() },
    errorMessage: (_err, fallback) => fallback,
}));

describe('permission-based product actions', () => {
    beforeEach(() => {
        api.get.mockReset().mockResolvedValue({ data: [{ id: 1, name: 'Laptop', price: '20.00', description: '' }] });
    });

    test('shows only actions included in the backend permission list', async () => {
        const permissions = new Set(['products_create', 'products_edit', 'orders_create']);
        useAuth.mockReturnValue({ hasPermission: (permission) => permissions.has(permission) });
        render(<SweetAlertProvider><Products /></SweetAlertProvider>);

        expect(await screen.findByText('Laptop')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Add product' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Edit' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Order' })).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Delete' })).not.toBeInTheDocument();
    });

    test('hides create and row actions when permissions are absent', async () => {
        useAuth.mockReturnValue({ hasPermission: () => false });
        render(<SweetAlertProvider><Products /></SweetAlertProvider>);
        expect(await screen.findByText('Laptop')).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Add product' })).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Edit' })).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Delete' })).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Order' })).not.toBeInTheDocument();
    });
});
