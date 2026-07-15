# Terraform — Super Ozono ERP (Fase 3 AWS foundation)

Infraestructura como código para el **runbook** multi-tenant en AWS:

| Recurso | Uso |
|---|---|
| VPC + 2 public / 2 private subnets | Red base (2 AZ) |
| IGW + NAT (opcional) | Salida internet |
| Security groups ALB / backend / RDS | Tráfico mínimo |
| RDS PostgreSQL 16 | Datos (privado, cifrado, backups 7d) |
| Secrets Manager | Password DB + SECRET_KEY app |
| SSM Parameter Store | version / CORS (no secretos) |
| ECR | Imágenes `api` y `frontend` |

**No incluye aún (Fase 5+):** ECS Fargate, ALB listeners, ACM, Route 53, CloudFront, S3 frontend.

## Prerrequisitos

1. Cuenta AWS + usuario/rol con permisos de VPC, RDS, ECR, Secrets, SSM, IAM.
2. [AWS CLI](https://aws.amazon.com/cli/) configurado (`aws configure` o SSO).
3. [Terraform](https://developer.hashicorp.com/terraform/install) ≥ 1.5.
4. Docker (para el `docker push` a ECR después del apply).

En el PC de desarrollo actual **no hay Docker ni Terraform instalados** — este directorio
queda listo para aplicar en una máquina con esas herramientas o en CI.

## Uso

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
# editar región, tamaños, etc.

terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### Push de imagen backend a ECR (después del apply)

```bash
AWS_REGION=us-east-1
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REPO=$(terraform output -raw ecr_backend_repository_url)

aws ecr get-login-password --region $AWS_REGION \
  | docker login --username AWS --password-stdin $ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com

docker build -t $REPO:latest ../../backend
docker push $REPO:latest
```

## Costos (orden de magnitud, us-east-1)

| Recurso | ~USD/mes |
|---|---|
| NAT Gateway | ~32 + datos |
| RDS db.t4g.micro | ~12–15 |
| ECR | bajo (almacenamiento) |
| Secrets Manager | ~0.40/secret |

Desactiva NAT (`enable_nat_gateway = false`) en experimentos si no necesitas salida.

## Seguridad

- RDS **no** es público (`publicly_accessible = false`).
- Password de BD **no** va a outputs ni a git; solo Secrets Manager.
- `terraform.tfvars` y `*.tfstate` están en `.gitignore`.
- Tras el primer deploy: rotar `seed_admin_password` en el secret `…/app`.

## Fase 5 — ECS + HTTPS (flags)

```hcl
enable_ecs   = true
enable_https = true
domain_name  = "api.tu-dominio.com"
route53_zone_id = "Z...."   # hosted zone

enable_github_oidc = true
github_org_repo    = "leonardeco/superozono-erp"
```

Tras `apply`:

1. Secret del repo GitHub: `AWS_ROLE_TO_ASSUME` = output `github_actions_role_arn`
2. Variables del repo: `AWS_REGION`, `ECR_REPOSITORY` (nombre corto del repo ECR)
3. Tag `v0.3.1` o *Run workflow* → Actions **Publish API image to ECR**
4. Actualizar servicio ECS / `api_image_tag` y re-apply si hace falta

HTTP en el ALB redirige a HTTPS cuando `enable_https` está activo.

## Fase 6 — Frontend S3 + CloudFront

```hcl
enable_frontend_cdn  = true
frontend_domain_name = "app.tu-dominio.com"  # opcional
# route53_zone_id ya definido arriba
```

Build local y sync (o usa Actions **Deploy frontend to CloudFront**):

```bash
cd frontend
VITE_API_URL=https://api.tu-dominio.com npm run build
aws s3 sync dist/ s3://$(terraform -chdir=../infra/terraform output -raw frontend_bucket_name)/ --delete
aws cloudfront create-invalidation \
  --distribution-id $(terraform -chdir=../infra/terraform output -raw cloudfront_distribution_id) \
  --paths "/*"
```

Si CloudFront enruta `/api/*` al ALB (`enable_ecs=true`), puedes dejar `VITE_API_URL` vacío
(same-origin).

Variables GitHub para el workflow frontend:

- `FRONTEND_S3_BUCKET`
- `CLOUDFRONT_DISTRIBUTION_ID`
- `VITE_API_URL` (opcional)

Ver `docs/hydraia/plans/2026-07-14-migracion-aws-runbook.md`.


