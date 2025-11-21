import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [RouterLink],
  template: `
    <section class="bg-gradient-to-br from-indigo-900/60 via-slate-900 to-slate-950 rounded-2xl border border-indigo-500/30 p-8 shadow-xl">
      <p class="text-xs uppercase tracking-[0.3rem] text-indigo-300">Serverless commerce</p>
      <h1 class="mt-3 text-3xl font-bold text-white">Catálogo headless listo para Cognito, API Gateway y Mercado Pago</h1>
      <p class="mt-3 text-slate-300 max-w-2xl">
        Angular 20 + Tailwind para experimentar el flujo completo: catálogo, ficha de producto, carrito, analytics y back office
        protegido con JWT.
      </p>
      <div class="mt-6 flex flex-wrap gap-3 text-sm">
        <a routerLink="/catalog" class="px-4 py-2 rounded-lg bg-indigo-500 text-white hover:bg-indigo-400 transition">Ver catálogo</a>
        <a routerLink="/auth" class="px-4 py-2 rounded-lg border border-indigo-400/60 text-indigo-200 hover:bg-indigo-500/10 transition">Colocar token Cognito</a>
        <a routerLink="/admin" class="px-4 py-2 rounded-lg border border-slate-700 text-slate-200 hover:bg-slate-800 transition">Entrar al back office</a>
      </div>
      <div class="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4 text-xs text-slate-300">
        <div class="rounded-xl border border-slate-800 p-4 bg-slate-900/40">API Gateway + Lambda proxy</div>
        <div class="rounded-xl border border-slate-800 p-4 bg-slate-900/40">Cognito JWT como Authorization</div>
        <div class="rounded-xl border border-slate-800 p-4 bg-slate-900/40">S3 + CloudFront para assets</div>
        <div class="rounded-xl border border-slate-800 p-4 bg-slate-900/40">Checkout con Mercado Pago</div>
      </div>
    </section>
  `
})
export class LandingComponent {}
