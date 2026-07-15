output "vpc_id" {
  value       = aws_vpc.main.id
  description = "ID de la VPC."
}

output "public_subnet_ids" {
  value       = aws_subnet.public[*].id
  description = "Subredes públicas (ALB)."
}

output "private_subnet_ids" {
  value       = aws_subnet.private[*].id
  description = "Subredes privadas (RDS + ECS)."
}

output "rds_endpoint" {
  value       = aws_db_instance.main.address
  description = "Hostname RDS (solo alcanzable desde la VPC)."
}

output "rds_port" {
  value = aws_db_instance.main.port
}

output "rds_security_group_id" {
  value = aws_security_group.rds.id
}

output "backend_security_group_id" {
  value = aws_security_group.backend.id
}

output "alb_security_group_id" {
  value = aws_security_group.alb.id
}

output "ecr_backend_repository_url" {
  value       = aws_ecr_repository.backend.repository_url
  description = "URL para docker push de la API."
}

output "ecr_frontend_repository_url" {
  value = aws_ecr_repository.frontend.repository_url
}

output "secrets_database_arn" {
  value       = aws_secretsmanager_secret.db.arn
  description = "ARN del secret con DATABASE_URL y password RDS."
}

output "secrets_app_arn" {
  value       = aws_secretsmanager_secret.app.arn
  description = "ARN del secret con SECRET_KEY de la app."
}

output "database_url_hint" {
  value       = "Ver secret ${aws_secretsmanager_secret.db.name} → database_url"
  description = "No se imprime la URL con password en outputs."
}
