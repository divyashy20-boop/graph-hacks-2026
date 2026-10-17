#!/usr/bin/env python3
"""Guarded Qwen Bedrock release for an existing Compose-managed Graphynx API.

Run from CloudShell: python3 scripts/qwen_release_cloudshell.py --inspect
Only after reviewing: python3 scripts/qwen_release_cloudshell.py --apply

Never modifies FalkorDB, other services, IAM, Lambda or Amplify.
Fails closed if production API container is not managed by Docker Compose.
"""
import argparse
import base64
import json
import sys
import time

import boto3

REGION = "ap-southeast-2"
ACCOUNT = "743976413697"
INSTANCE = "i-0ab21892ca194d4ca"
MODEL = "qwen.qwen3-32b-v1:0"
OVERLAY = """services:
  api:
    environment:
      UGI_PROVIDER: bedrock
      UGI_ALLOW_PAID_CALLS: "true"
      UGI_MODEL_ID: qwen.qwen3-32b-v1:0
      UGI_AWS_REGION: ap-southeast-2
      UGI_INPUT_PRICE: "0.1545"
      UGI_OUTPUT_PRICE: "0.6180"
      UGI_DAILY_COST_LIMIT: "0.25"
      UGI_MAX_MODEL_CALLS: "8"
      UGI_MAX_OUTPUT_TOKENS: "2250"
      UGI_MAX_INPUT_TOKENS: "12000"
      UGI_EXTRACTION_WINDOWS: "1"
"""
REMOTE = r'''
import base64, copy, json, os, pathlib, subprocess, sys, time

APPLY = %APPLY%
OVERLAY = base64.b64decode("%ENCODED%").decode()

def cmd(args, cwd=None, check=True, timeout=90):
    p = subprocess.run(args, capture_output=True, text=True,
                       cwd=cwd, timeout=timeout)
    if check and p.returncode:
        raise RuntimeError(f"COMMAND_FAILED:{args[0]}:{p.stderr[-600:]}")
    return p

def inspect(name):
    r = cmd(["docker", "inspect", name])
    return json.loads(r.stdout)[0]

def stop(reason):
    print("RELEASE_ABORTED_NO_CHANGES:", reason, flush=True)
    sys.exit(0)

current = inspect("graphynx-api")
db = inspect("graphynx-db")
if not db.get("State", {}).get("Running"):
    stop("graphynx-db not running")
labels = current.get("Config", {}).get("Labels") or {}
project = labels.get("com.docker.compose.project")
service = labels.get("com.docker.compose.service")
workdir = labels.get("com.docker.compose.project.working_dir")
source_files = labels.get("com.docker.compose.project.config_files", "")
if not (project and service == "api" and workdir and source_files):
    stop("graphynx-api is not confirmed Compose service 'api'; need deployment manifest, no blind docker recreate")

files = [p.strip() for p in source_files.split(",") if p.strip()]
if not files or not all(pathlib.Path(x).is_file() for x in files):
    stop("original Compose files are missing; cannot safely deploy")
if not pathlib.Path(workdir).is_dir():
    stop("Compose working directory absent")

base = ["docker", "compose", "-p", project]
for file in files:
    base.extend(["-f", file])
original = json.loads(cmd(base + ["config", "--format", "json"], workdir).stdout)
old_svc = original["services"].get("api")
if not old_svc:
    stop("original service api not found")

overlay_dir = pathlib.Path("/tmp") / "graphynx-qwen-guarded-release"
overlay_dir.mkdir(mode=0o700, exist_ok=True)
overlay_path = overlay_dir / "compose.qwen.yaml"
overlay_path.write_text(OVERLAY)
overlay_path.chmod(0o600)
new_args = base + ["-f", str(overlay_path)]
proposed = json.loads(cmd(new_args + ["config", "--format", "json"], workdir).stdout)
expected = {
    "UGI_PROVIDER": "bedrock",
    "UGI_ALLOW_PAID_CALLS": "true",
    "UGI_MODEL_ID": "qwen.qwen3-32b-v1:0",
    "UGI_AWS_REGION": "ap-southeast-2",
    "UGI_INPUT_PRICE": "0.1545",
    "UGI_OUTPUT_PRICE": "0.6180",
    "UGI_DAILY_COST_LIMIT": "0.25",
    "UGI_MAX_MODEL_CALLS": "8",
    "UGI_MAX_OUTPUT_TOKENS": "2250",
    "UGI_MAX_INPUT_TOKENS": "12000",
    "UGI_EXTRACTION_WINDOWS": "1",
}
if set(original["services"]) != set(proposed["services"]):
    stop("service inventory differs after overlay")
other0 = copy.deepcopy(original)
other1 = copy.deepcopy(proposed)
oldenv = other0["services"]["api"].pop("environment", {})
newenv = other1["services"]["api"].pop("environment", {})
if other0 != other1:
    stop("non-environment compose config would change")
if any(newenv.get(k) != v for k,v in expected.items()):
    stop("Qwen environment not reflected in Compose config")
if {k:v for k,v in oldenv.items() if k not in expected} != \
   {k:v for k,v in newenv.items() if k not in expected}:
    stop("unexpected environment change beyond allowlist")
for label in ("UGI_API_KEYS", "UGI_GUIDED_AGENT_ENABLED", "UGI_MEMORY_ENABLED",
              "UGI_MEMORY_PATH", "UGI_IDENTITY_LEDGER", "UGI_IDENTITY_RESOLUTION",
              "UGI_SCHEMA_WRITES", "UGI_OPEN_PREDICATES"):
    if oldenv.get(label) != newenv.get(label):
        stop("protected setting changed: " + label)

print("RELEASE_PREFLIGHT_OK")
print("INSTANCE API Compose project/service:", project, service)
print("DATABASE_RUNNING:", bool(db["State"]["Running"]))
print("MODEL:", expected["UGI_MODEL_ID"])
print("PRESERVES_DB_AND_VOLUMES: yes")
print("PROTECTED_CONFIG_UNCHANGED: yes")

if not APPLY:
    print("INSPECT_ONLY_COMPLETE_NO_CHANGES")
    sys.exit(0)

print("API_ONLY_RECREATE_START; graphynx-db untouched")
try:
    cmd(new_args + ["up", "-d", "--no-deps", "--no-build", "api"],
        cwd=workdir, timeout=180)
    ok = False
    for _ in range(30):
        time.sleep(2)
        after = inspect("graphynx-api")
        if not after.get("State", {}).get("Running"):
            continue
        env = dict(s.split("=", 1) for s in after["Config"]["Env"] if "=" in s)
        if any(env.get(k) != v for k, v in expected.items()):
            raise RuntimeError("new container missing expected Qwen environment")
        health = after.get("State", {}).get("Health", {}).get("Status")
        if health not in (None, "healthy"):
            continue
        result = cmd(["docker", "exec", "graphynx-api", "python", "-c",
                      "from ugi.models import Settings; s=Settings(); "
                      "assert s.provider=='bedrock' and s.model_id=='qwen.qwen3-32b-v1:0'"], check=False)
        if result.returncode == 0:
            ok = True
            break
    if not ok:
        raise RuntimeError("API startup/Settings/health never passed")
    print("QWEN_RELEASE_APPLIED_API_HEALTHY")
except Exception as error:
    print("QWEN_RELEASE_FAILED_ROLLING_BACK_API:", type(error).__name__, str(error)[:450])
    try:
        cmd(base + ["up", "-d", "--no-deps", "--no-build", "api"], workdir, timeout=180)
        print("API_ROLLBACK_REQUESTED_CHECK_HEALTH_MANUALLY")
    except Exception as rollback_error:
        print("ROLLBACK_FAILED_ESCALATE:", str(rollback_error)[:450])
'''

def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--inspect", action="store_true")
    group.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    sts = boto3.client("sts")
    actual = sts.get_caller_identity()["Account"]
    if actual != ACCOUNT:
        raise SystemExit(f"WRONG_ACCOUNT: expected {ACCOUNT}, got {actual}")
    ec2 = boto3.client("ec2", region_name=REGION)
    inst = ec2.describe_instances(InstanceIds=[INSTANCE])["Reservations"][0]["Instances"][0]
    tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}
    if tags.get("Project") != "GraphynxAI":
        raise SystemExit("INSTANCE_TAG_MISMATCH")
    state = inst["State"]["Name"]
    print("TARGET:", INSTANCE, "STATE:", state, flush=True)
    if state != "running":
        raise SystemExit("TARGET_NOT_RUNNING: use the existing approved EC2 start flow; no automatic start")
    ssm = boto3.client("ssm", region_name=REGION)
    program = REMOTE.replace("%APPLY%", "True" if args.apply else "False").replace(
        "%ENCODED%", base64.b64encode(OVERLAY.encode()).decode())
    shell = "python3 - <<'REMOTE_PY'\n" + program + "\nREMOTE_PY"
    sent = ssm.send_command(InstanceIds=[INSTANCE], DocumentName="AWS-RunShellScript",
                            Parameters={"commands": [shell]}, TimeoutSeconds=240)
    cid = sent["Command"]["CommandId"]
    print("SSM_COMMAND_ID:", cid, flush=True)
    for i in range(85):
        time.sleep(3)
        try:
            r = ssm.get_command_invocation(CommandId=cid, InstanceId=INSTANCE)
        except ssm.exceptions.InvocationDoesNotExist:
            continue
        if r["Status"] in ("Success", "Failed", "Cancelled", "TimedOut"):
            print("SSM_STATUS:", r["Status"])
            print("OUTPUT:\n", r.get("StandardOutputContent", "")[-14000:])
            if r.get("StandardErrorContent"):
                print("STDERR:\n", r["StandardErrorContent"][-2000:])
            if r["Status"] != "Success":
                raise SystemExit("SSM_COMMAND_NOT_SUCCESS: inspect before any retry")
            return
    raise SystemExit("SSM_STILL_RUNNING: check original command ID; do not rerun --apply")

if __name__ == "__main__":
    main()
