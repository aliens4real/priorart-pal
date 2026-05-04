# infra/ — AWS CDK app

This is the **infrastructure-as-code** for PriorArt Pal. Every AWS resource (VPC, RDS, App Runner, API Gateway, Cognito, S3, CloudFront, alarms) is declared in Python here. We never click around in the AWS console.

## What CDK is (and why we use it)

**AWS CDK** is a framework for defining cloud infrastructure in real programming languages. You write Python; CDK compiles it to a **CloudFormation template** (a giant YAML/JSON file describing every resource and how they relate). AWS reads that template and creates / updates / deletes the resources to match.

Think of it like a build system for your cloud account: you describe what you want, it figures out how to get there from the current state.

The key vocabulary:

- **App** — the top-level container (`app.py`)
- **Stack** — a deployable unit (one stack = one CloudFormation stack). We split by lifecycle: VPC rarely changes, App Runner changes often, Cognito should never be recreated.
- **Construct** — a reusable building block (e.g., `aws_cdk.aws_rds.DatabaseInstance`). CDK ships hundreds of these.

## Stack layout

| Stack | What it owns | Lifecycle |
|---|---|---|
| `NetworkingStack` | VPC, subnets, security groups | Rarely changes |
| `SecretsStack` | Secrets Manager entries (Voyage / Cohere / Anthropic / DB) | Changes when adding providers |
| `DatabaseStack` | RDS Postgres + pgvector enabling | Schema changes via migrations, not CDK |
| `AuthStack` | Cognito User Pool + Hosted UI | **Never recreate** (would lose users) |
| `AppRunnerStack` | ECR repo + App Runner service + VPC connector | Changes per deploy |
| `ApiGatewayStack` | HTTP API + JWT authorizer + usage plans | Changes when API surface changes |
| `FrontendStack` | S3 + CloudFront + OAC | Changes per frontend deploy |
| `MonitoringStack` | CloudWatch dashboard + billing alarm refs | Changes as we add metrics |

## Workflow

```bash
cd infra
uv sync                  # install Python deps
uv run cdk synth         # compile to CloudFormation, show output (no AWS calls beyond ListStacks)
uv run pytest            # unit-test the stack definitions
```

**Deploy** — only after Michael says "yes, deploy":

```bash
uv run cdk diff          # show what would change vs deployed state
uv run cdk deploy <Stack> # deploy one stack (or --all)
```

## First-time bootstrap

CDK needs a one-time setup in your AWS account/region called **bootstrapping**. It creates:

- An S3 bucket for staging large assets (Lambda code, Docker images, etc.)
- An ECR repo for container images
- IAM roles CDK uses to deploy

Run once per account/region:

```bash
uv run cdk bootstrap aws://<ACCOUNT_ID>/us-east-1
```

This is AWS-mutating and costs ~$1/mo (S3 storage). **Requires Michael's "yes, deploy".**

## Cost expectations (steady-state)

| Resource | Estimate |
|---|---|
| RDS db.t4g.micro | ~$13/mo |
| App Runner (1 vCPU / 2GB, low traffic) | ~$5–10/mo |
| Secrets Manager (4 secrets) | ~$1.60/mo |
| CloudFront + S3 (low traffic) | <$1/mo |
| CDK bootstrap S3 | ~$1/mo |
| **Subtotal infra** | **~$22/mo** |
| AI APIs (Voyage + Cohere + Anthropic, low traffic) | ~$5–15/mo |
| **Total target** | **<$50/mo** |
