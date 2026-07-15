# Plan — Fase 3: fundamentos AWS (Terraform)

- **Goal:** VPC + RDS + ECR + Secrets versionados en `infra/terraform/`.
- **No ejecutado en este PC:** faltan AWS CLI, Terraform y Docker.

## Entregado

| Path | Contenido |
|---|---|
| `infra/terraform/vpc.tf` | VPC, subnets, IGW, NAT opcional |
| `infra/terraform/security_groups.tf` | ALB / backend / RDS |
| `infra/terraform/rds.tf` | Postgres 16 privado + cifrado |
| `infra/terraform/secrets.tf` | Secrets Manager + SSM |
| `infra/terraform/ecr.tf` | Repos API y frontend |
| `infra/terraform/outputs.tf` | IDs y ARNs útiles |
| `infra/terraform/README.md` | Cómo init/plan/apply y push ECR |

## Checkpoint (cuando se aplique)

- [ ] `terraform apply` OK
- [ ] RDS solo alcanzable desde SG backend
- [ ] Secret DB tiene `database_url`
- [ ] `docker push` a ECR backend OK

## Siguiente

Fase 5: ECS Fargate + ALB + HTTPS (ACM + dominio).
