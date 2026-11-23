export function passwordPolicyError(password) {
    if (password.length < 8) return 'Password must be at least 8 characters.';
    if (!/[A-Z]/.test(password)) return 'Password must contain an uppercase letter.';
    if (!/[^A-Za-z0-9]/.test(password)) return 'Password must contain a special character.';
    return '';
}

export function usernamePolicyError(username) {
    const value = username.trim();
    if (value.length < 3) return 'Username must be at least 3 characters.';
    if (value.length > 10) return 'Username must be no more than 10 characters.';
    return '';
}
