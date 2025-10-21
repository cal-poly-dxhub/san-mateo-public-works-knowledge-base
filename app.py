#!/usr/bin/env python3
import subprocess
import sys

import aws_cdk as cdk

# Extract prompts before deployment
try:
    subprocess.run([sys.executable, "extract_prompts.py"], check=True)
    print("Prompts extracted successfully")
except subprocess.CalledProcessError as e:
    print(f"Failed to extract prompts: {e}")
    sys.exit(1)

from project_management_stack import ProjectManagementStack

app = cdk.App()
ProjectManagementStack(app, "ProjectManagementStack")

app.synth()
