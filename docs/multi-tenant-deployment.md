# Despliegue multi-tenant parametrizado

Este documento resume cómo extender los stacks de CloudFormation y el pipeline para que un *wizard* de onboarding pueda crear un tenant end-to-end utilizando `tenantId` como parámetro principal.

## Plantillas de CloudFormation

### Backend (`cloudformation/backend.yml`)
- Se agrega el parámetro `TenantId` y se propaga como tag en las tablas DynamoDB, lo que facilita la trazabilidad y permite usar un stack por tenant.
- Se introduce la tabla central `tenants` para almacenar el estado y metadatos de cada tenant (stage, dominio, hosted zone). El rol de Lambda obtiene permisos para leer/escribir en ella y la función expone variables de entorno `TENANT_ID` y `TENANTS_TABLE` para su consumo.
- El nombre del API Gateway incluye el `TenantId` para evitar colisiones entre stacks.

### Frontend (`cloudformation/frontend.yml`)
- Nuevos parámetros: `TenantId`, `BaseDomainName` y `HostedZoneId` para componer dominios dinámicos `tenantId.BaseDomainName` cuando el wizard no envía un dominio completo (`DomainName`).
- Se añaden condiciones que permiten omitir el alias en CloudFront cuando no hay dominio y crear automáticamente un registro A en Route53 apuntando al distribuidor cuando `BaseDomainName` y `HostedZoneId` están presentes.
- Se publica un output `TenantDomain` que devuelve el dominio efectivo (subdominio generado o dominio proporcionado).

## Pipeline de onboarding

El workflow GitHub Actions `.github/workflows/tenant-onboarding.yml` se dispara manualmente (`workflow_dispatch`) con inputs del wizard:

1. **Deploy backend**: llama a `cloudformation/backend.yml` pasando `TenantId`, artefacto de Lambda y authorizer Cognito. Usa `CAPABILITY_NAMED_IAM` para crear el rol de ejecución.
2. **Deploy frontend**: despliega `cloudformation/frontend.yml` con el bucket del tenant, certificado ACM y parámetros de dominio/subdominio. Si se especifica `BaseDomainName` y `HostedZoneId`, también crea el registro en Route53.
3. **Persistencia de tenant**: registra el tenant en la tabla `tenants` (condición `attribute_not_exists` para evitar duplicados) guardando stage, dominio efectivo y hosted zone.
4. **Salida para el wizard**: imprime la URL de API, dominio CloudFront y dominio asignado para que el wizard pueda enlazarlo con el onboarding.

## Consideraciones de subdominios

- El certificado ACM debe incluir `*.BaseDomainName` (y/o los dominios completos personalizados) para que CloudFront valide los aliases.
- Si se usa dominio personalizado (`DomainName`), el wizard debe asegurarse de crear el registro DNS correspondiente fuera de Route53 o proporcionar `HostedZoneId` para que el workflow lo cree.
- Los buckets del frontend siguen siendo únicos; se recomienda concatenar `tenantId` y la región para evitar colisiones globales.
