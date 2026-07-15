# Fase 6 — Frontend SPA en S3 + CloudFront (sin tocar código React).
# enable_frontend_cdn = true cuando haya dominio o baste el dominio *.cloudfront.net

variable "enable_frontend_cdn" {
  type        = bool
  description = "Crear bucket S3 + distribución CloudFront para el SPA."
  default     = false
}

variable "frontend_domain_name" {
  type        = string
  description = "Dominio del SPA (ej. app.superozono.example.com). Vacío = solo dominio CloudFront."
  default     = ""
}

variable "frontend_price_class" {
  type        = string
  description = "PriceClass_100 (NA/EU barato) | PriceClass_200 | PriceClass_All"
  default     = "PriceClass_100"
}

locals {
  frontend_enabled = var.enable_frontend_cdn
  frontend_has_custom_domain = (
    var.enable_frontend_cdn && var.frontend_domain_name != "" && var.route53_zone_id != ""
  )
}

resource "aws_s3_bucket" "frontend" {
  count  = local.frontend_enabled ? 1 : 0
  bucket = "${local.name}-frontend-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name = "${local.name}-frontend"
  }
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  count  = local.frontend_enabled ? 1 : 0
  bucket = aws_s3_bucket.frontend[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "frontend" {
  count  = local.frontend_enabled ? 1 : 0
  bucket = aws_s3_bucket.frontend[0].id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "frontend" {
  count  = local.frontend_enabled ? 1 : 0
  bucket = aws_s3_bucket.frontend[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Certificado CloudFront (siempre us-east-1)
resource "aws_acm_certificate" "frontend" {
  count    = local.frontend_has_custom_domain ? 1 : 0
  provider = aws.us_east_1

  domain_name       = var.frontend_domain_name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "${local.name}-frontend-cert"
  }
}

resource "aws_route53_record" "frontend_acm_validation" {
  for_each = local.frontend_has_custom_domain ? {
    for dvo in aws_acm_certificate.frontend[0].domain_validation_options :
    dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  } : {}

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = var.route53_zone_id
}

resource "aws_acm_certificate_validation" "frontend" {
  count    = local.frontend_has_custom_domain ? 1 : 0
  provider = aws.us_east_1

  certificate_arn         = aws_acm_certificate.frontend[0].arn
  validation_record_fqdns = [for r in aws_route53_record.frontend_acm_validation : r.fqdn]
}

resource "aws_cloudfront_origin_access_control" "frontend" {
  count = local.frontend_enabled ? 1 : 0

  name                              = "${local.name}-frontend-oac"
  description                       = "OAC S3 frontend Super Ozono"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "frontend" {
  count = local.frontend_enabled ? 1 : 0

  enabled             = true
  is_ipv6_enabled     = true
  comment             = "${local.name} SPA"
  default_root_object = "index.html"
  price_class         = var.frontend_price_class
  aliases             = local.frontend_has_custom_domain ? [var.frontend_domain_name] : []

  origin {
    domain_name              = aws_s3_bucket.frontend[0].bucket_regional_domain_name
    origin_id                = "s3-frontend"
    origin_access_control_id = aws_cloudfront_origin_access_control.frontend[0].id
  }

  # Opcional: API en el mismo dominio vía /api → ALB (solo si ECS está activo)
  dynamic "origin" {
    for_each = var.enable_ecs ? [1] : []
    content {
      domain_name = aws_lb.api[0].dns_name
      origin_id   = "alb-api"

      custom_origin_config {
        http_port              = 80
        https_port             = 443
        origin_protocol_policy = var.enable_https ? "https-only" : "http-only"
        origin_ssl_protocols   = ["TLSv1.2"]
      }
    }
  }

  dynamic "ordered_cache_behavior" {
    for_each = var.enable_ecs ? [1] : []
    content {
      path_pattern     = "/api/*"
      allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
      cached_methods   = ["GET", "HEAD", "OPTIONS"]
      target_origin_id = "alb-api"

      forwarded_values {
        query_string = true
        headers      = ["Authorization", "Origin", "Accept", "Content-Type"]
        cookies {
          forward = "all"
        }
      }

      viewer_protocol_policy = "redirect-to-https"
      min_ttl                = 0
      default_ttl            = 0
      max_ttl                = 0
      compress               = true
    }
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "s3-frontend"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
    compress               = true
  }

  # SPA: rutas del cliente → index.html
  custom_error_response {
    error_code            = 403
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }

  custom_error_response {
    error_code            = 404
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = !local.frontend_has_custom_domain
    acm_certificate_arn = local.frontend_has_custom_domain ? (
      aws_acm_certificate_validation.frontend[0].certificate_arn
    ) : null
    ssl_support_method       = local.frontend_has_custom_domain ? "sni-only" : null
    minimum_protocol_version = local.frontend_has_custom_domain ? "TLSv1.2_2021" : null
  }

  tags = {
    Name = "${local.name}-frontend-cdn"
  }
}

data "aws_iam_policy_document" "frontend_s3" {
  count = local.frontend_enabled ? 1 : 0

  statement {
    sid    = "AllowCloudFrontServicePrincipal"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.frontend[0].arn}/*"]
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.frontend[0].arn]
    }
  }
}

resource "aws_s3_bucket_policy" "frontend" {
  count  = local.frontend_enabled ? 1 : 0
  bucket = aws_s3_bucket.frontend[0].id
  policy = data.aws_iam_policy_document.frontend_s3[0].json
}

resource "aws_route53_record" "frontend" {
  count = local.frontend_has_custom_domain ? 1 : 0

  zone_id = var.route53_zone_id
  name    = var.frontend_domain_name
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.frontend[0].domain_name
    zone_id                = aws_cloudfront_distribution.frontend[0].hosted_zone_id
    evaluate_target_health = false
  }
}

# Ampliar política del rol GitHub para deploy S3 + invalidación CF
data "aws_iam_policy_document" "github_frontend_deploy" {
  count = var.enable_github_oidc && local.frontend_enabled ? 1 : 0

  statement {
    sid = "S3Sync"
    actions = [
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
      "s3:GetObject",
    ]
    resources = [
      aws_s3_bucket.frontend[0].arn,
      "${aws_s3_bucket.frontend[0].arn}/*",
    ]
  }

  statement {
    sid       = "CFInvalidate"
    actions   = ["cloudfront:CreateInvalidation"]
    resources = [aws_cloudfront_distribution.frontend[0].arn]
  }
}

resource "aws_iam_role_policy" "github_frontend_deploy" {
  count  = var.enable_github_oidc && local.frontend_enabled ? 1 : 0
  name   = "${local.name}-github-frontend"
  role   = aws_iam_role.github_actions[0].id
  policy = data.aws_iam_policy_document.github_frontend_deploy[0].json
}

output "frontend_bucket_name" {
  value       = try(aws_s3_bucket.frontend[0].id, null)
  description = "Bucket S3 del SPA (sync desde CI)."
}

output "cloudfront_distribution_id" {
  value       = try(aws_cloudfront_distribution.frontend[0].id, null)
  description = "ID CloudFront para invalidaciones."
}

output "cloudfront_domain_name" {
  value       = try(aws_cloudfront_distribution.frontend[0].domain_name, null)
  description = "Dominio *.cloudfront.net del SPA."
}

output "frontend_url" {
  value = local.frontend_has_custom_domain ? "https://${var.frontend_domain_name}" : (
    local.frontend_enabled ? "https://${aws_cloudfront_distribution.frontend[0].domain_name}" : null
  )
  description = "URL pública del frontend."
}
