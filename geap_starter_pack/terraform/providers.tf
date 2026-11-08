provider "google" {
  project = var.project_id
  region  = var.region

  # Send the API quota and billing to the mini build project.
  user_project_override = true
  billing_project       = var.project_id
}

data "google_project" "this" {
  project_id = var.project_id
}

locals {
  project_number = data.google_project.this.number

  # Labels for the resources that support labels. Clean-up uses `terraform destroy`.
  labels = {
    starter-pack = "mini-build"
  }
}
