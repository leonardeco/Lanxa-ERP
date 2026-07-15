# RDS PostgreSQL en subredes privadas. Password generado y guardado en Secrets Manager.

resource "random_password" "db" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "aws_db_subnet_group" "main" {
  name       = "${local.name}-db-subnets"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "${local.name}-db-subnets"
  }
}

resource "aws_db_instance" "main" {
  identifier = "${local.name}-postgres"

  engine         = "postgres"
  engine_version = "16"
  instance_class = var.db_instance_class

  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_allocated_storage * 2
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = var.db_name
  username = var.db_username
  password = random_password.db.result

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false
  multi_az               = var.db_multi_az

  # TLS: preferir conexiones SSL desde la app (asyncpg/ssl)
  # parameter group default de Postgres ya permite force_ssl vía custom group (opcional).

  backup_retention_period = 7
  backup_window           = "07:00-08:00" # UTC
  maintenance_window      = "sun:08:00-sun:09:00"

  deletion_protection = true
  skip_final_snapshot = false
  final_snapshot_identifier = "${local.name}-final"

  # Performance Insights opcional (costo)
  performance_insights_enabled = false

  tags = {
    Name = "${local.name}-postgres"
  }

  lifecycle {
    ignore_changes = [
      # Evita recrear al rotar password solo en Secrets Manager
      password,
    ]
  }
}
