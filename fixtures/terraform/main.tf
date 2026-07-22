resource "aws_s3_bucket" "public_assets" {
  bucket = "iac-scan-example-public-assets"
  acl    = "public-read"
}
