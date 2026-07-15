# Security groups: ALB (futuro) → backend → RDS. Sin abrir RDS a internet.

resource "aws_security_group" "alb" {
  name        = "${local.name}-alb-sg"
  description = "ALB ingress HTTPS/HTTP (Fase 5); preparado desde Fase 3"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = length(var.allowed_admin_cidrs) > 0 ? var.allowed_admin_cidrs : ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP (redirect a HTTPS en ALB)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = length(var.allowed_admin_cidrs) > 0 ? var.allowed_admin_cidrs : ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name}-alb-sg"
  }
}

resource "aws_security_group" "backend" {
  name        = "${local.name}-backend-sg"
  description = "ECS/Fargate tasks — solo tráfico desde ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "API desde ALB"
    from_port       = var.backend_container_port
    to_port         = var.backend_container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    description = "Salida (RDS, Secrets, ECR, internet vía NAT)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name}-backend-sg"
  }
}

resource "aws_security_group" "rds" {
  name        = "${local.name}-rds-sg"
  description = "PostgreSQL solo desde backend SG"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Postgres desde backend"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.backend.id]
  }

  # Sin egress especial necesario para RDS
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name}-rds-sg"
  }
}
