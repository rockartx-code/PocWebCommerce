import { inject } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivateFn, Router, RouterStateSnapshot } from '@angular/router';
import { AuthService } from '../../shared/auth.service';
import { TenantContextService } from '../../shared/tenant-context.service';

function requestedTenantId(route: ActivatedRouteSnapshot, context: TenantContextService): string | null {
  return route.queryParamMap.get('tenantId') || route.paramMap.get('tenantId') || context.tenantId();
}

export const enforceTenantIsolationGuard: CanActivateFn = (
  route: ActivatedRouteSnapshot,
  state: RouterStateSnapshot
) => {
  const router = inject(Router);
  const auth = inject(AuthService);
  const context = inject(TenantContextService);

  const tokenTenant = auth.tenantId;
  if (!tokenTenant) {
    return router.createUrlTree(['/auth'], { queryParams: { redirectTo: state.url } });
  }

  const tenantFromRoute = requestedTenantId(route, context);
  if (tenantFromRoute && tenantFromRoute !== tokenTenant) {
    context.setTenantId(tokenTenant);
    return router.createUrlTree(['/catalog'], { queryParams: { tenantId: tokenTenant } });
  }

  context.setTenantId(tokenTenant);
  return true;
};
