import { Injectable, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class AuthService {
  token = signal<string | null>(null);

  constructor() {
    const persisted = localStorage.getItem('cognito_token');
    if (persisted) {
      this.token.set(persisted);
    }
  }

  setToken(value: string) {
    this.token.set(value);
    localStorage.setItem('cognito_token', value);
  }

  clear() {
    this.token.set(null);
    localStorage.removeItem('cognito_token');
  }

  get authorizationHeader() {
    const value = this.token();
    return value ? { Authorization: `Bearer ${value}` } : {};
  }
}
