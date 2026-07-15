# Plan — Fase 6: frontend S3 + CloudFront

## Entregado

| Pieza | Path |
|---|---|
| S3 privado + OAC + CF | `infra/terraform/frontend_cdn.tf` |
| ACM us-east-1 + DNS | mismo archivo (si hay dominio) |
| Comportamiento `/api/*` → ALB | si `enable_ecs=true` |
| SPA 403/404 → index.html | custom_error_response |
| CI deploy | `.github/workflows/frontend-cdn.yml` |
| IAM GitHub S3+CF | policy extra en OIDC role |

## Flags

```hcl
enable_frontend_cdn  = true   # default false
frontend_domain_name = ""     # vacío = dominio cloudfront.net
```

## Checklist

- [ ] `terraform apply` con CDN on
- [ ] Variables GitHub S3 + CF ID
- [ ] Build con `VITE_API_URL` correcto
- [ ] Smoke `https://app…/` y login
