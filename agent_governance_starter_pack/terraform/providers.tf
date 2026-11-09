provider "google" {
  project = var.project_id
  region  = var.region

  # Send the API quota and billing to the mini build project.
  user_project_override = true
  billing_project       = var.project_id
}

locals {
  # A variable, not a data source, so that `terraform plan` makes no API call
  # before the APIs are on.
  project_number = var.project_number

  # Labels for the resources that support labels. Clean-up uses `terraform destroy`.
  labels = {
    starter-pack = "mini-build"
  }
}
