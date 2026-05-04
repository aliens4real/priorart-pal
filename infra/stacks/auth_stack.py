"""Cognito User Pool + Hosted UI.

Pattern note: Cognito Hosted UI is a managed sign-in/sign-up page hosted
by AWS. The frontend redirects to it for auth, the user signs in, Cognito
redirects back with a code, the frontend exchanges that for JWTs (id token,
access token, refresh token). API Gateway then validates the access token
on every request via the JWT authorizer in ApiGatewayStack.

We deliberately split this out so it never gets recreated — losing this
stack means losing all user accounts.
"""
from __future__ import annotations

from aws_cdk import Duration, RemovalPolicy, Stack
from aws_cdk import aws_cognito as cognito
from constructs import Construct


class AuthStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        project: str,
        hosted_ui_prefix: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.user_pool = cognito.UserPool(
            self,
            "UserPool",
            user_pool_name=f"{project}-users",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            password_policy=cognito.PasswordPolicy(
                min_length=12,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True,
            ),
            mfa=cognito.Mfa.OPTIONAL,
            mfa_second_factor=cognito.MfaSecondFactor(
                sms=False, otp=True
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.RETAIN,  # NEVER delete user data
        )

        # Admin group — used by /admin/metrics endpoint
        cognito.CfnUserPoolGroup(
            self,
            "AdminGroup",
            user_pool_id=self.user_pool.user_pool_id,
            group_name="admin",
            description="Administrators with access to /admin/* endpoints",
            precedence=1,
        )

        self.user_pool.add_domain(
            "HostedDomain",
            cognito_domain=cognito.CognitoDomainOptions(domain_prefix=hosted_ui_prefix),
        )

        # The app client is the per-application registration. Frontend uses
        # this client_id when redirecting to the Hosted UI.
        self.user_pool_client = self.user_pool.add_client(
            "WebClient",
            user_pool_client_name=f"{project}-web",
            generate_secret=False,  # SPA — no client secret
            auth_flows=cognito.AuthFlow(user_srp=True),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(authorization_code_grant=True),
                scopes=[cognito.OAuthScope.OPENID, cognito.OAuthScope.EMAIL, cognito.OAuthScope.PROFILE],
                callback_urls=["http://localhost:5173/callback"],
                logout_urls=["http://localhost:5173/"],
            ),
            access_token_validity=Duration.hours(1),
            id_token_validity=Duration.hours(1),
            refresh_token_validity=Duration.days(30),
            prevent_user_existence_errors=True,
        )
