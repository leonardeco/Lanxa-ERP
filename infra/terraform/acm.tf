# ACM + HTTPS en el ALB (Fase 5/6).
# Requiere un dominio en Route 53 (o validación DNS manual).
# enable_https = true solo cuando exista domain_name y enable_ecs = true.

variable "enable_https" {
  type        = bool
  description = "Crear certificado ACM y listener HTTPS en el ALB."
  default     = false
}

variable "domain_name" {
  type        = string
  description = "Dominio del API (ej. api.superozono.example.com). Vacío si no hay HTTPS."
  default     = ""
}

variable "route53_zone_id" {
  type        = string
  description = "Hosted zone ID de Route 53 para validación DNS del certificado (opcional si validas a mano)."
  default     = ""
}

resource "aws_acm_certificate" "api" {
  count = var.enable_https && var.enable_ecs && var.domain_name != "" ? 1 : 0

  domain_name       = var.domain_name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "${local.name}-api-cert"
  }
}

resource "aws_route53_record" "acm_validation" {
  for_each = (
    var.enable_https && var.enable_ecs && var.domain_name != "" && var.route53_zone_id != ""
    ? {
      for dvo in aws_acm_certificate.api[0].domain_validation_options :
      dvo.domain_name => {
        name   = dvo.resource_record_name
        record = dvo.resource_record_value
        type   = dvo.resource_record_type
      }
    }
    : {}
  )

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = var.route53_zone_id
}

resource "aws_acm_certificate_validation" "api" {
  count = (
    var.enable_https && var.enable_ecs && var.domain_name != "" && var.route53_zone_id != ""
    ? 1
    : 0
  )

  certificate_arn         = aws_acm_certificate.api[0].arn
  validation_record_fqdns = [for r in aws_route53_record.acm_validation : r.fqdn]
}

resource "aws_lb_listener" "https" {
  count = var.enable_https && var.enable_ecs && var.domain_name != "" ? 1 : 0

  load_balancer_arn = aws_lb.api[0].arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn = (
    var.route53_zone_id != ""
    ? aws_acm_certificate_validation.api[0].certificate_arn
    : aws_acm_certificate.api[0].arn
  )

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api[0].arn
  }
}

resource "aws_route53_record" "api" {
  count = (
    var.enable_https && var.enable_ecs && var.domain_name != "" && var.route53_zone_id != ""
    ? 1
    : 0
  )

  zone_id = var.route53_zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_lb.api[0].dns_name
    zone_id                = aws_lb.api[0].zone_id
    evaluate_target_health = true
  }
}

output "acm_certificate_arn" {
  value       = try(aws_acm_certificate.api[0].arn, null)
  description = "ARN del certificado ACM (null si enable_https=false)."
}

output "api_https_url" {
  value       = var.enable_https && var.domain_name != "" ? "https://${var.domain_name}" : null
  description = "URL HTTPS del API cuando el dominio está configurado."
}
