output"alb_dns_name" {
  description = "The public URL of the Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "ecr_repository_url" {
  description = "URL of the ECR container repository"
  value       = aws_ecr_repository.app.repository_url
}

output "s3_bucket_name" {
  description = "The S3 bucket name created for model registry artifact storage"
  value       = aws_s3_bucket.model_registry.id
}

output "ecs_cluster_name" {
  description = "Name of the ECS Fargate cluster"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "Name of the ECS service running the backend"
  value       = aws_ecs_service.main.name
}
