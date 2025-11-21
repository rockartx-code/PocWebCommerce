import { Injectable, signal } from '@angular/core';

interface JwtClaims {
  exp?: number;
  ['custom:tenantId']?: string;
  tenantId?: string;
  [key: string]: unknown;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  token = signal<string | null>(null);
  private claims = signal<JwtClaims | null>(null);

  constructor() {
    const persisted = localStorage.getItem('cognito_token');
    this.setToken(persisted);
  }

  setToken(value: string | null) {
    if (!value) {
      this.clear();
      return;
    }
    const claims = this.decodeClaims(value);
    if (!claims) {
      this.clear();
      return;
    }
    if (this.isExpired(claims.exp)) {
      this.clear();
      return;
    }
    if (!this.extractTenantId(claims)) {
      this.clear();
      return;
    }
    this.token.set(value);
    this.claims.set(claims);
    localStorage.setItem('cognito_token', value);
  }

  clear() {
    this.token.set(null);
    this.claims.set(null);
    localStorage.removeItem('cognito_token');
  }

  get authorizationHeader() {
    const value = this.token();
    const claims = this.claims();
    const tenantId = claims ? this.extractTenantId(claims) : null;
    if (!value || !claims || this.isExpired(claims.exp) || !tenantId) {
      this.clear();
      return {};
    }
    return { Authorization: `Bearer ${value}`, 'X-Tenant-Id': tenantId };
  }

  private decodeClaims(token: string): JwtClaims | null {
    const parts = token.split('.');
    if (parts.length < 2) {
      return null;
    }
    try {
      const payload = atob(parts[1].replace(/-/g, '+').replace(/_/g, '/'));
      return JSON.parse(payload);
    } catch (err) {
      console.error('Failed to parse JWT payload', err);
      return null;
    }
  }

  private isExpired(exp?: number): boolean {
    if (!exp) {
      return false;
    }
    const nowSeconds = Math.floor(Date.now() / 1000);
    return exp <= nowSeconds;
  }

  private extractTenantId(claims: JwtClaims): string | null {
    return (claims['custom:tenantId'] || claims.tenantId || null) ?? null;
  }
}
