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

## Siguiente (Fase 5)

Módulo ECS Fargate + ALB apuntando a:

- `backend_security_group_id`
- `private_subnet_ids`
- secrets ARNs
- `ecr_backend_repository_url`

Ver `docs/hydraia/plans/2026-07-14-migracion-aws-runbook.md`.
