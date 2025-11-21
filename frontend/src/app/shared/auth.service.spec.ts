import { AuthService } from './auth.service';

function buildToken(payload: Record<string, unknown>) {
  const encode = (obj: Record<string, unknown>) =>
    btoa(JSON.stringify(obj)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  const header = encode({ alg: 'none', typ: 'JWT' });
  const body = encode(payload);
  return `${header}.${body}.`;
}

describe('AuthService', () => {
  let service: AuthService;

  beforeEach(() => {
    localStorage.clear();
    service = new AuthService();
    service.clear();
  });

  it('expone headers con Authorization y X-Tenant-Id cuando el token es válido', () => {
    const token = buildToken({ exp: Math.floor(Date.now() / 1000) + 3600, 'custom:tenantId': 't-001' });
    service.setToken(token);

    expect(service.authorizationHeader).toEqual({ Authorization: `Bearer ${token}`, 'X-Tenant-Id': 't-001' });
  });

  it('limpia el token cuando está expirado', () => {
    const token = buildToken({ exp: Math.floor(Date.now() / 1000) - 60, 'custom:tenantId': 't-002' });
    service.setToken(token);

    expect(service.token()).toBeNull();
    expect(service.authorizationHeader).toEqual({});
  });

  it('rechaza tokens sin tenantId', () => {
    const token = buildToken({ exp: Math.floor(Date.now() / 1000) + 3600, sub: 'user-123' });
    service.setToken(token);

    expect(service.token()).toBeNull();
    expect(service.authorizationHeader).toEqual({});
  });
});
