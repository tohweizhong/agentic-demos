terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# VIOLATION: Storage bucket permits public access from the internet (IM8 Reform ns-2)
resource "google_storage_bucket" "citizen_documents" {
  name          = "gcc-agency-citizen-documents-prod"
  location      = "asia-southeast1" # Singapore region
  force_destroy = false

  # Non-compliant: Public access prevention should be "enforced"
  public_access_prevention = "inherited"

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }
}

# Non-compliant: Public read access granted to allUsers
resource "google_storage_bucket_iam_member" "public_read" {
  bucket = google_storage_bucket.citizen_documents.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}
