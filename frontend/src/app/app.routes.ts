import { Routes } from '@angular/router';
import { LandingComponent } from './features/landing/landing.component';
import { CatalogComponent } from './features/catalog/catalog.component';
import { ProductDetailComponent } from './features/product/product-detail.component';
import { CartComponent } from './features/cart/cart.component';
import { AnalyticsDashboardComponent } from './features/analytics/analytics-dashboard.component';
import { AuthPanelComponent } from './features/auth/auth-panel.component';
import { AdminDashboardComponent } from './features/admin/admin-dashboard.component';

export const appRoutes: Routes = [
  { path: '', component: LandingComponent, pathMatch: 'full' },
  { path: 'catalog', component: CatalogComponent },
  { path: 'product/:id', component: ProductDetailComponent },
  { path: 'cart', component: CartComponent },
  { path: 'analytics', component: AnalyticsDashboardComponent },
  { path: 'auth', component: AuthPanelComponent },
  { path: 'admin', component: AdminDashboardComponent },
  { path: '**', redirectTo: '' }
];
