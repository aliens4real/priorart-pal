"""S3 + CloudFront for the React SPA.

Pattern note: For a static SPA, the cheapest production-quality hosting is
S3 (storage) + CloudFront (global CDN + HTTPS). The OAC (Origin Access
Control) pattern keeps the bucket fully private — only CloudFront can read
it, never the public internet.
"""
from __future__ import annotations

from aws_cdk import CfnOutput, RemovalPolicy, Stack
from aws_cdk import aws_cloudfront as cf
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_s3 as s3
from constructs import Construct


class FrontendStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        project: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.bucket = s3.Bucket(
            self,
            "WebBucket",
            bucket_name=None,  # let CDK generate to avoid global-name conflicts
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            enforce_ssl=True,
        )

        self.distribution = cf.Distribution(
            self,
            "Distribution",
            comment=f"{project} frontend",
            default_root_object="index.html",
            default_behavior=cf.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(self.bucket),
                viewer_protocol_policy=cf.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cf.CachePolicy.CACHING_OPTIMIZED,
                compress=True,
            ),
            error_responses=[
                # SPA routing — always serve index.html for client-side routes
                cf.ErrorResponse(http_status=404, response_http_status=200,
                                 response_page_path="/index.html"),
                cf.ErrorResponse(http_status=403, response_http_status=200,
                                 response_page_path="/index.html"),
            ],
            price_class=cf.PriceClass.PRICE_CLASS_100,  # NA + EU only — cheap
        )

        CfnOutput(self, "BucketName", value=self.bucket.bucket_name)
        CfnOutput(
            self,
            "DistributionUrl",
            value=f"https://{self.distribution.distribution_domain_name}",
        )
