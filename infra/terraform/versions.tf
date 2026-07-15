terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Descomentar cuando tengas un bucket S3 de estado remoto:
  # backend "s3" {
  #   bucket         = "superozono-tfstate-ACCOUNT"
  #   key            = "prod/foundation/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "superozono-tf-locks"
  #   encrypt        = true
  # }
}
