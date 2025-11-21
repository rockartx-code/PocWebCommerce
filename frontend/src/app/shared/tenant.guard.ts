import { inject } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivateFn, Router, RouterStateSnapshot } from '@angular/router';
import { TenantContextService } from './tenant-context.service';
import { AuthService } from './auth.service';

function resolveTenant(route: ActivatedRouteSnapshot, auth: AuthService, context: TenantContextService): string | null {
  const routeTenant = route.queryParamMap.get('tenantId') || route.paramMap.get('tenantId');
  if (routeTenant) {
    context.setTenantId(routeTenant);
    return routeTenant;
  }
  const tokenTenant = auth.tenantId;
  if (tokenTenant) {
    context.setTenantId(tokenTenant);
    return tokenTenant;
  }
  return context.tenantId();
}

export const ensureTenantGuard: CanActivateFn = (route: ActivatedRouteSnapshot, state: RouterStateSnapshot) => {
  const router = inject(Router);
  const auth = inject(AuthService);
  const context = inject(TenantContextService);

  const tenant = resolveTenant(route, auth, context);
  if (tenant) {
    return true;
  }

  return router.createUrlTree(['/wizard'], { queryParams: { redirectTo: state.url } });
};
