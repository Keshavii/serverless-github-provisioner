# ============================================================================
# LAMBDA LAYER - PYTHON DEPENDENCIES
# Contains all Python packages from requirements-lambda.txt
# ============================================================================

# Null resource to build the Lambda layer
resource "null_resource" "build_lambda_layer" {
  triggers = {
    requirements = filemd5("${var.requirements_path}/requirements-lambda.txt")
  }

  provisioner "local-exec" {
    command = <<-EOT
      rm -rf ${path.module}/layer/python && mkdir -p ${path.module}/layer/python
      pip3 install \
        --platform manylinux2014_x86_64 \
        --target ${path.module}/layer/python \
        --implementation cp \
        --python-version ${var.lambda_runtime} \
        --only-binary=:all: \
        --upgrade \
        --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.python.org \
        -r ${var.requirements_path}/requirements-lambda.txt
    EOT
  }
}

# Archive the layer
data "archive_file" "lambda_layer" {
  type        = "zip"
  source_dir  = "${path.module}/layer"
  output_path = "${path.module}/lambda-layer.zip"
  
  depends_on = [null_resource.build_lambda_layer]
}

# Lambda Layer
resource "aws_lambda_layer_version" "dependencies" {
  filename            = data.archive_file.lambda_layer.output_path
  layer_name          = "${var.project_name}-python-dependencies"
  compatible_runtimes = ["python${var.lambda_runtime}"]
  source_code_hash    = data.archive_file.lambda_layer.output_base64sha256

  description = "Python dependencies for GitHub repository automation"

  depends_on = [data.archive_file.lambda_layer]
}
