# Fase 5 (borrador) — ECS Fargate + ALB
# Depende de: vpc, security_groups, ecr, secrets, rds (Fase 3).
# Activar con: enable_ecs = true en tfvars (default false hasta tener cuenta/costos OK).

variable "enable_ecs" {
  type        = bool
  description = "Crear cluster ECS + ALB + servicio API (Fase 5)."
  default     = false
}

variable "api_image_tag" {
  type        = string
  description = "Tag de imagen en ECR para el servicio API."
  default     = "latest"
}

variable "api_cpu" {
  type    = number
  default = 256
}

variable "api_memory" {
  type    = number
  default = 512
}

variable "api_desired_count" {
  type    = number
  default = 1
}

# ── CloudWatch logs ──────────────────────────────────────
resource "aws_cloudwatch_log_group" "api" {
  count             = var.enable_ecs ? 1 : 0
  name              = "/ecs/${local.name}-api"
  retention_in_days = 30
}

# ── IAM execution role (pull ECR + secrets) ──────────────
data "aws_iam_policy_document" "ecs_assume" {
  count = var.enable_ecs ? 1 : 0
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_execution" {
  count              = var.enable_ecs ? 1 : 0
  name               = "${local.name}-ecs-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume[0].json
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  count      = var.enable_ecs ? 1 : 0
  role       = aws_iam_role.ecs_execution[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "ecs_execution_secrets" {
  count = var.enable_ecs ? 1 : 0
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.db.arn, aws_secretsmanager_secret.app.arn]
  }
}

resource "aws_iam_role_policy" "ecs_execution_secrets" {
  count  = var.enable_ecs ? 1 : 0
  name   = "${local.name}-ecs-secrets"
  role   = aws_iam_role.ecs_execution[0].id
  policy = data.aws_iam_policy_document.ecs_execution_secrets[0].json
}

resource "aws_iam_role" "ecs_task" {
  count              = var.enable_ecs ? 1 : 0
  name               = "${local.name}-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume[0].json
}

# ── Cluster + ALB ────────────────────────────────────────
resource "aws_ecs_cluster" "main" {
  count = var.enable_ecs ? 1 : 0
  name  = "${local.name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_lb" "api" {
  count              = var.enable_ecs ? 1 : 0
  name               = "${local.name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id
}

resource "aws_lb_target_group" "api" {
  count       = var.enable_ecs ? 1 : 0
  name        = "${local.name}-api-tg"
  port        = var.backend_container_port
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    matcher             = "200"
  }
}

resource "aws_lb_listener" "http" {
  count             = var.enable_ecs ? 1 : 0
  load_balancer_arn = aws_lb.api[0].arn
  port              = 80
  protocol          = "HTTP"

  # Con HTTPS activo: redirigir todo a 443. Sin certificado: forward HTTP (dev/staging).
  dynamic "default_action" {
    for_each = var.enable_https && var.domain_name != "" ? [1] : []
    content {
      type = "redirect"
      redirect {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
  }

  dynamic "default_action" {
    for_each = var.enable_https && var.domain_name != "" ? [] : [1]
    content {
      type             = "forward"
      target_group_arn = aws_lb_target_group.api[0].arn
    }
  }
}

# ── Task definition ──────────────────────────────────────
resource "aws_ecs_task_definition" "api" {
  count                    = var.enable_ecs ? 1 : 0
  family                   = "${local.name}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = aws_iam_role.ecs_execution[0].arn
  task_role_arn            = aws_iam_role.ecs_task[0].arn

  container_definitions = jsonencode([
    {
      name      = "api"
      image     = "${aws_ecr_repository.backend.repository_url}:${var.api_image_tag}"
      essential = true
      portMappings = [
        {
          containerPort = var.backend_container_port
          protocol      = "tcp"
        }
      ]
      environment = [
        { name = "DEBUG", value = "false" },
        { name = "ACCESS_TOKEN_EXPIRE_MINUTES", value = "15" },
      ]
      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = "${aws_secretsmanager_secret.db.arn}:database_url::"
        },
        {
          name      = "SECRET_KEY"
          valueFrom = "${aws_secretsmanager_secret.app.arn}:secret_key::"
        },
        {
          name      = "SEED_ADMIN_PASSWORD"
          valueFrom = "${aws_secretsmanager_secret.app.arn}:seed_admin_password::"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.api[0].name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "api"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "curl -fsS http://127.0.0.1:${var.backend_container_port}/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])
}

resource "aws_ecs_service" "api" {
  count           = var.enable_ecs ? 1 : 0
  name            = "${local.name}-api"
  cluster         = aws_ecs_cluster.main[0].id
  task_definition = aws_ecs_task_definition.api[0].arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.backend.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api[0].arn
    container_name   = "api"
    container_port   = var.backend_container_port
  }

  depends_on = [aws_lb_listener.http]

  lifecycle {
    ignore_changes = [desired_count]
  }
}

output "alb_dns_name" {
  value       = try(aws_lb.api[0].dns_name, null)
  description = "DNS del ALB (HTTP). Activar enable_ecs = true."
}

output "ecs_cluster_name" {
  value = try(aws_ecs_cluster.main[0].name, null)
}
