resource "aws_ecr_repository" "app" {
  name                 = "devopsify-example-app"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    App = "devopsify-example-app"
  }
}

output "ecr_repo_url" {
  value = aws_ecr_repository.app.repository_url
}