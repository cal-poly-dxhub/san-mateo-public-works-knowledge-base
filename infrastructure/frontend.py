from aws_cdk import aws_ec2 as ec2, aws_ecs as ecs, aws_ecs_patterns as ecs_patterns, aws_ecr_assets as ecr_assets
from constructs import Construct


class FrontendHosting(Construct):
    def __init__(self, scope: Construct, construct_id: str, api_url: str) -> None:
        super().__init__(scope, construct_id)

        vpc = ec2.Vpc(self, "VPC", max_azs=2, nat_gateways=0)

        cluster = ecs.Cluster(self, "Cluster", vpc=vpc)

        self.service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "Service",
            cluster=cluster,
            cpu=512,
            memory_limit_mib=1024,
            desired_count=1,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_asset(
                    "./frontend",
                    platform=ecr_assets.Platform.LINUX_AMD64,
                ),
                container_port=3000,
                environment={
                    "NEXT_PUBLIC_API_URL": api_url,
                },
            ),
            public_load_balancer=True,
            assign_public_ip=True,
        )

        self.url = self.service.load_balancer.load_balancer_dns_name
