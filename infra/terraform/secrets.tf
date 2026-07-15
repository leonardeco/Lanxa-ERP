# Secrets Manager: credenciales BD + plantilla de secretos de la app.
# La app en ECS leerá estos ARNs (Fase 5).

resource "aws_secretsmanager_secret" "db" {
  name                    = "${local.name}/database"
  description             = "Credenciales RDS PostgreSQL — Super Ozono ERP"
  recovery_window_in_days = 7

  tags = {
    Name = "${local.name}-db-secret"
  }
}

resource "aws_secretsmanager_secret_version" "db" {
  secret_id = aws_secretsmanager_secret.db.id
  secret_string = jsonencode({
    engine   = "postgres"
    host     = aws_db_instance.main.address
    port     = aws_db_instance.main.port
    dbname   = var.db_name
    username = var.db_username
    password = random_password.db.result
    # URL lista para FastAPI / SQLAlchemy async
    # Construir URL en la app o con secret values; evitar password en logs de TF.
    # Formato: postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DB
    host     = aws_db_instance.main.address
    port     = aws_db_instance.main.port
    database = var.db_name
  })
}

resource "random_password" "app_secret_key" {
  length  = 64
  special = false
}

resource "aws_secretsmanager_secret" "app" {
  name                    = "${local.name}/app"
  description             = "SECRET_KEY y config sensible de la app"
  recovery_window_in_days = 7

  tags = {
    Name = "${local.name}-app-secret"
  }
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    secret_key             = random_password.app_secret_key.result
    seed_admin_password    = "CHANGE_ME_AFTER_FIRST_DEPLOY"
    access_token_minutes   = 15
    refresh_token_days     = 30
    debug                  = false
  })
}

# Parámetros no secretos (SSM)
resource "aws_ssm_parameter" "app_version" {
  name  = "/${local.name}/app/version"
  type  = "String"
  value = "0.3.0"

  tags = {
    Name = "${local.name}-app-version"
  }
}

resource "aws_ssm_parameter" "cors_origins" {
  name  = "/${local.name}/app/cors_origins"
  type  = "String"
  value = "https://app.example.com"

  tags = {
    Name = "${local.name}-cors"
  }
}
