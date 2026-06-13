variable "aws_region" {
  description = "The AWS region to deploy resources into"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "The deployment environment (e.g. staging, production)"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "forest-fire-detection"
}

variable "container_port" {
  description = "Port exposed by the FastAPI container"
  type        = number
  default     = 8000
}

variable "cpu_units" {
  description = "Amount of CPU for the ECS task definition (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "memory_limit" {
  description = "Amount of memory for the ECS task definition in MB"
  type        = number
  default     = 2048
}

variable "db_allocated_storage" {
  description = "The allocated storage in gigabytes for RDS"
  type        = number
  default     = 20
}

variable "db_instance_class" {
  description = "The database instance type for RDS"
  type        = string
  default     = "db.t3.medium"
}
