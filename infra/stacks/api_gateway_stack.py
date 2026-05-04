"""API Gateway HTTP API + Cognito JWT authorizer.

Pattern note: HTTP API (v2) is the cheap, fast successor to REST API (v1).
We use it for two things:

1. **JWT validation** — the Cognito-issued access token is validated on
   every request before it reaches App Runner. Saves App Runner from doing
   it and keeps the auth boundary at the edge.

2. **Throttling / usage plans** — API Gateway throttles requests per route
   to keep AI costs bounded. (HTTP API has account-level throttling out of
   the box; route-level throttling we'll wire in Phase 3.)

Phase 1 wires the HTTP API skeleton with the JWT authorizer. Routes get
attached in Phase 2 once the FastAPI app has real endpoints.
"""
from __future__ import annotations

from aws_cdk import CfnOutput, Stack
from aws_cdk import aws_apigatewayv2 as apigw
from aws_cdk import aws_apigatewayv2_authorizers as apigw_auth
from aws_cdk import aws_cognito as cognito
from constructs import Construct


class ApiGatewayStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        project: str,
        user_pool: cognito.IUserPool,
        user_pool_client: cognito.IUserPoolClient,
        app_runner_url: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.api = apigw.HttpApi(
            self,
            "HttpApi",
            api_name=f"{project}-api",
            description="HTTP API → App Runner FastAPI",
            cors_preflight=apigw.CorsPreflightOptions(
                allow_origins=["http://localhost:5173"],
                allow_methods=[apigw.CorsHttpMethod.ANY],
                allow_headers=["authorization", "content-type"],
            ),
            disable_execute_api_endpoint=False,
        )

        self.jwt_authorizer = apigw_auth.HttpJwtAuthorizer(
            "CognitoAuthorizer",
            jwt_issuer=f"https://cognito-idp.{self.region}.amazonaws.com/{user_pool.user_pool_id}",
            jwt_audience=[user_pool_client.user_pool_client_id],
        )

        self.api_id = self.api.api_id

        CfnOutput(self, "ApiUrl", value=self.api.api_endpoint)
