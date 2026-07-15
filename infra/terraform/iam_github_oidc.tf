# Rol IAM para GitHub Actions → ECR (OIDC, sin access keys largas).
# enable_github_oidc = true cuando el repo ya tenga Actions configurado.

variable "enable_github_oidc" {
  type        = bool
  description = "Crear OIDC provider + rol para GitHub Actions (ECR push)."
  default     = false
}

variable "github_org_repo" {
  type        = string
  description = "owner/repo de GitHub (ej. leonardeco/superozono-erp)."
  default     = "leonardeco/superozono-erp"
}

data "aws_caller_identity" "current" {}

resource "aws_iam_openid_connect_provider" "github" {
  count = var.enable_github_oidc ? 1 : 0

  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["ffffffffffffffffffffffffffffffffffffffff"]
}

data "aws_iam_policy_document" "github_assume" {
  count = var.enable_github_oidc ? 1 : 0

  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github[0].arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values = [
        "repo:${var.github_org_repo}:ref:refs/heads/main",
        "repo:${var.github_org_repo}:ref:refs/tags/v*",
        "repo:${var.github_org_repo}:environment:*",
      ]
    }
  }
}

resource "aws_iam_role" "github_actions" {
  count              = var.enable_github_oidc ? 1 : 0
  name               = "${local.name}-github-actions"
  assume_role_policy = data.aws_iam_policy_document.github_assume[0].json
}

data "aws_iam_policy_document" "github_ecr" {
  count = var.enable_github_oidc ? 1 : 0

  statement {
    sid = "ECRAuth"
    actions = [
      "ecr:GetAuthorizationToken",
    ]
    resources = ["*"]
  }

  statement {
    sid = "ECRPush"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "ecr:PutImage",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload",
      "ecr:DescribeRepositories",
    ]
    resources = [
      aws_ecr_repository.backend.arn,
      aws_ecr_repository.frontend.arn,
    ]
  }
}

resource "aws_iam_role_policy" "github_ecr" {
  count  = var.enable_github_oidc ? 1 : 0
  name   = "${local.name}-github-ecr"
  role   = aws_iam_role.github_actions[0].id
  policy = data.aws_iam_policy_document.github_ecr[0].json
}

output "github_actions_role_arn" {
  value       = try(aws_iam_role.github_actions[0].arn, null)
  description = "Poner en secret AWS_ROLE_TO_ASSUME del repo GitHub."
}
