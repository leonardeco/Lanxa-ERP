variable "aws_region" {
  type        = string
  description = "Región AWS (ej. us-east-1 o us-east-2)."
  default     = "us-east-1"
}

variable "project_name" {
  type        = string
  description = "Prefijo de nombres de recursos."
  default     = "superozono"
}

variable "environment" {
  type        = string
  description = "dev | staging | prod"
  default     = "prod"
}

variable "vpc_cidr" {
  type        = string
  description = "CIDR de la VPC."
  default     = "10.20.0.0/16"
}

variable "db_name" {
  type        = string
  description = "Nombre de la base PostgreSQL en RDS."
  default     = "superozono_erp"
}

variable "db_username" {
  type        = string
  description = "Usuario master de RDS (password se genera y guarda en Secrets Manager)."
  default     = "superozono"
}

variable "db_instance_class" {
  type        = string
  description = "Clase de instancia RDS. Empezar barato."
  default     = "db.t4g.micro"
}

variable "db_allocated_storage" {
  type        = number
  description = "GB de almacenamiento inicial RDS."
  default     = 20
}

variable "db_multi_az" {
  type        = bool
  description = "Multi-AZ (más caro; activar en prod serio)."
  default     = false
}

variable "enable_nat_gateway" {
  type        = bool
  description = "NAT Gateway para subredes privadas (costo fijo ~$32/mes). false = solo VPC endpoints / sin salida."
  default     = true
}

variable "backend_container_port" {
  type        = number
  description = "Puerto del contenedor FastAPI (para security group del backend / ECS)."
  default     = 8000
}

variable "allowed_admin_cidrs" {
  type        = list(string)
  description = "CIDRs que pueden llegar al ALB/bastion en el futuro (vacío = solo SG internos)."
  default     = []
}
