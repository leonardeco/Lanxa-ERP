# Plan — HTTPS/ACM + CI publish ECR

## Entregado

| Pieza | Path |
|---|---|
| ACM + listener 443 + redirect 80→443 | `infra/terraform/acm.tf` (+ cambio en `ecs.tf`) |
| OIDC GitHub → IAM role ECR | `infra/terraform/iam_github_oidc.tf` |
| Workflow publish | `.github/workflows/ecr-publish.yml` |

## Flags (todos default false / sin costo extra)

- `enable_ecs`
- `enable_https` + `domain_name` + `route53_zone_id`
- `enable_github_oidc` + `github_org_repo`

## Checklist cuando haya AWS

- [ ] `terraform apply` foundation (Fase 3)
- [ ] `enable_github_oidc=true` → copiar `github_actions_role_arn` a secrets del repo
- [ ] Push imagen (tag `v*` o workflow_dispatch)
- [ ] `enable_ecs=true` + imagen en ECR
- [ ] `enable_https=true` + DNS
- [ ] Smoke `https://api…/health`
