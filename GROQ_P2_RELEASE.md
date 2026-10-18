# Graphynx Groq GPT-OSS 120B P2 local selection

Qualified by the frozen four-document proxy, NOT a production reliability guarantee.
P2 extraction: `openai/gpt-oss-120b`, reasoning `low`, strict JSON Schema,
whole 2250 tokens / split 1550 tokens. Production uses the official Groq SDK.
The actual application extraction prompt/chunking is not guaranteed byte-identical
to frozen tournament prompts. Existing evidence/UNKNOWN semantics are unchanged.

## Runtime settings (apply only after live backup and inspection)

```dotenv
UGI_PROVIDER=groq
UGI_ALLOW_PAID_CALLS=true
UGI_MODEL_ID=openai/gpt-oss-120b
UGI_INPUT_PRICE=0.15
UGI_OUTPUT_PRICE=0.60
UGI_MAX_MODEL_CALLS=8
UGI_MAX_OUTPUT_TOKENS=2250
UGI_MAX_INPUT_TOKENS=12000
UGI_EXTRACTION_WINDOWS=1
UGI_GROQ_SPLIT_MAX_OUTPUT_TOKENS=1550
```

`GROQ_API_KEY` must be securely supplied to EC2 at runtime; never commit it.
Do not blindly run Docker Compose on existing manual-Docker production.
Verify live instance, patched DynamoDB lifetime guard and agent route.
Preserve all volumes, nginx, judge access and rollback image.
A feature-branch push does not auto-deploy or update the static Amplify site.
