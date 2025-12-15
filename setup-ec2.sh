#!/bin/bash
set -e

echo "=== Knowledge Base - EC2 Setup Script ==="
echo "Prerequisites: AWS credentials must be configured (~/.aws/credentials or environment variables)"

# Update system
sudo yum update -y
echo "✓ System updated"

# Install Git
sudo yum install -y git
echo "✓ Git installed"

# Install Docker
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
echo "✓ Docker installed and started"

# Install Node.js 18
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo yum install -y nodejs
echo "✓ Node.js $(node --version) installed"

# Install Python 3.9+
sudo yum install -y python3 python3-pip
echo "✓ Python $(python3 --version) installed"

# Install AWS CDK CLI
sudo npm install -g aws-cdk
echo "✓ AWS CDK $(cdk --version) installed"

# Clone the repository
cd ~
git clone https://github.com/cal-poly-dxhub/san-mateo-public-works-knowledge-base
cd san-mateo-public-works-knowledge-base
echo "✓ Repository cloned"

# Install Python dependencies
pip3 install -r requirements.txt
echo "✓ Python dependencies installed"

# Bootstrap and deploy with Docker group
echo ""
echo "=== Running CDK bootstrap and deploy ==="
sg docker -c "cdk bootstrap && cdk deploy --require-approval never"

echo ""
echo "=== Deployment complete! ==="
echo "Look for the CloudFront URL in the outputs above."
