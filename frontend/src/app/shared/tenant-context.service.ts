import { Injectable, signal } from '@angular/core';
import { AuthService } from './auth.service';

const STORAGE_KEY = 'active_tenant_id';

@Injectable({ providedIn: 'root' })
export class TenantContextService {
  private persisted = localStorage.getItem(STORAGE_KEY);
  private tenantSignal = signal<string | null>(this.persisted);

  constructor(private auth: AuthService) {}

  tenantId(): string | null {
    return this.tenantSignal() || this.auth.tenantId;
  }

  setTenantId(value: string | null) {
    if (!value) {
      localStorage.removeItem(STORAGE_KEY);
      this.tenantSignal.set(null);
      return;
    }
    localStorage.setItem(STORAGE_KEY, value);
    this.tenantSignal.set(value);
  }
}
