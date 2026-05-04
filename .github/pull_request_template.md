## What & why

<!-- One paragraph: what does this PR change, and what problem does it solve? -->

## Scope

<!-- Bulleted list of the actual changes. Helps the reviewer triage quickly. -->

-

## Test plan

<!-- How did you verify this works? Be specific. -->

- [ ] `make test` passes locally
- [ ] CI green
- [ ] Manually exercised the changed surface (curl / browser / `cdk synth`)

## AWS / cost impact

<!-- Required for any PR that touches infra/. Skip for code-only PRs. -->

- New resources created: <!-- e.g., +1 RDS instance, +1 NAT gateway -->
- Estimated $/month delta: <!-- e.g., +$0, +$5 -->
- Any AWS-mutating commands required to deploy: <!-- e.g., cdk deploy <Stack> -->

## Rollback

<!-- How do you back out if this breaks production? -->

## Linked notes

- Related issue / NOTES.md entry: <!-- # or NOTES.md L## -->
