import secrets

from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_ecr_assets as ecr_assets,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_elasticloadbalancingv2 as elbv2,
)
from constructs import Construct

# Generate a secret header value (fixed at synth time)
CLOUDFRONT_SECRET_HEADER = secrets.token_hex(32)


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

        vpc = ec2.Vpc(self, "VPC", max_azs=2, nat_gateways=0)

        # VPC endpoints for private subnet access to AWS services
        vpc.add_interface_endpoint(
            "EcrEndpoint", service=ec2.InterfaceVpcEndpointAwsService.ECR
        )
        vpc.add_interface_endpoint(
            "EcrDockerEndpoint", service=ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER
        )
        vpc.add_gateway_endpoint(
            "S3Endpoint", service=ec2.GatewayVpcEndpointAwsService.S3
        )
        vpc.add_interface_endpoint(
            "LogsEndpoint", service=ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS
        )

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
        )

        # Configure ALB to only accept requests with the secret header
        # Remove default action and add header-based routing
        listener = self.service.listener
        
        # Add a rule that checks for the secret header
        listener.add_action(
            "AllowCloudFrontOnly",
            priority=1,
            conditions=[
                elbv2.ListenerCondition.http_header(
                    "X-CloudFront-Secret", [CLOUDFRONT_SECRET_HEADER]
                )
            ],
            action=elbv2.ListenerAction.forward([self.service.target_group]),
        )
        
        # Change default action to return 403
        cfn_listener = listener.node.default_child
        cfn_listener.default_actions = [
            {"type": "fixed-response", "fixedResponseConfig": {"statusCode": "403", "contentType": "text/plain", "messageBody": "Forbidden"}}
        ]

        # CloudFront distribution in front of ALB
        self.distribution = cloudfront.Distribution(
            self,
            "Distribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.LoadBalancerV2Origin(
                    self.service.load_balancer,
                    protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY,
                    custom_headers={"X-CloudFront-Secret": CLOUDFRONT_SECRET_HEADER},
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER,
            ),
        )

        self.url = self.distribution.distribution_domain_name
