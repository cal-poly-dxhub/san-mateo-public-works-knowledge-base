from aws_cdk import (
    aws_cloudfront as cloudfront,
)
from aws_cdk import (
    aws_cloudfront_origins as origins,
)
from aws_cdk import (
    aws_ec2 as ec2,
)
from aws_cdk import (
    aws_ecr_assets as ecr_assets,
)
from aws_cdk import (
    aws_ecs as ecs,
)
from aws_cdk import (
    aws_ecs_patterns as ecs_patterns,
)
from constructs import Construct


class FrontendHosting(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        api_url: str,
        user_pool_id: str,
        user_pool_client_id: str,
        region: str,
    ) -> None:
        super().__init__(scope, construct_id)

        vpc = ec2.Vpc(
            self,
            "VPC",
            max_azs=2,
            nat_gateways=1,
        )

        cluster = ecs.Cluster(self, "Cluster", vpc=vpc)

        task_security_group = ec2.SecurityGroup(
            self,
            "TaskSecurityGroup",
            vpc=vpc,
            description="Security group for Fargate tasks",
            allow_all_outbound=True,
        )

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
                    exclude=["node_modules", ".next"],
                ),
                container_port=3000,
                environment={
                    "NEXT_PUBLIC_API_URL": api_url,
                    "NEXT_PUBLIC_USER_POOL_ID": user_pool_id,
                    "NEXT_PUBLIC_USER_POOL_CLIENT_ID": user_pool_client_id,
                    "NEXT_PUBLIC_REGION": region,
                },
            ),
            public_load_balancer=True,
            assign_public_ip=False,
            task_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[task_security_group],
        )

        # Restrict ALB to only accept traffic from CloudFront
        self.alb_security_group = (
            self.service.load_balancer.connections.security_groups[0]
        )

        # CloudFront distribution in front of ALB
        self.distribution = cloudfront.Distribution(
            self,
            "Distribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.LoadBalancerV2Origin(
                    self.service.load_balancer,
                    protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY,
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER,
            ),
        )

        self.url = self.distribution.distribution_domain_name
