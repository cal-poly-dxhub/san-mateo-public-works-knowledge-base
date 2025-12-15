# A setup script to be used on an EC2 to easily deploy this solution
#!/bin/bash
set -e

echo "=== Knowledge Base - EC2 Setup Script ==="
echo "Prerequisites: AWS credentials must be configured (~/.aws/credentials or environment variables)"

# Update system
sudo yum update -y

# Install Git
sudo yum install -y git

# Install Docker
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# Install Node.js 18
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo yum install -y nodejs

# Install Python 3.9+ (Amazon Linux 2023 has Python 3.9+ by default)
sudo yum install -y python3 python3-pip

# Install AWS CDK CLI
sudo npm install -g aws-cdk

# Clone the repository
cd ~
git clone https://github.com/cal-poly-dxhub/san-mateo-public-works-knowledge-base
cd san-mateo-public-works-knowledge-base

# Install Python dependencies
pip3 install -r requirements.txt

# Bootstrap and deploy with Docker group
echo ""
echo "=== Running CDK bootstrap and deploy ==="
sg docker -c "cdk deploy"

echo ""
echo "=== Deployment complete! ==="
echo "Look for the CloudFront URL in the outputs above."
