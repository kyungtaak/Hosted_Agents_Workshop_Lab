"""
Foundry agent deployment helper — creates or updates a hosted agent definition
in Microsoft Foundry using the Python SDK.

Usage:
    python scripts/deploy_foundry_agent.py \
        --project-endpoint <endpoint> \
        --agent-name hosted-agent-readiness-coach \
        --image <acr-name>.azurecr.io/workshoplab-agent:lab4

    Or with inline JSON definition from PowerShell wrapper:
    python scripts/deploy_foundry_agent.py \
        --project-endpoint <endpoint> \
        --agent-name hosted-agent-readiness-coach \
        --agent-definition '{"kind":"hosted",...}'
"""

import argparse
import json
import os
import sys

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import HostedAgentDefinition, ProtocolVersionRecord, AgentProtocol
from azure.identity import DefaultAzureCredential


def parse_args():
    parser = argparse.ArgumentParser(description="Deploy a Foundry hosted agent.")
    parser.add_argument("--project-endpoint", default=os.environ.get("AZURE_AI_PROJECT_ENDPOINT"))
    parser.add_argument("--agent-name", default="hosted-agent-readiness-coach")
    parser.add_argument("--agent-definition", default=None)
    parser.add_argument("--image", default=None)
    parser.add_argument("--cpu", default="1")
    parser.add_argument("--memory", default="2Gi")
    parser.add_argument("--set", dest="replacements", action="append", default=[])
    return parser.parse_args()


def main():
    args = parse_args()

    project_endpoint = args.project_endpoint
    if not project_endpoint:
        print("ERROR: --project-endpoint or AZURE_AI_PROJECT_ENDPOINT must be set.", file=sys.stderr)
        sys.exit(1)

    # Resolve image and env vars from inline definition or CLI args
    if args.agent_definition:
        definition = json.loads(args.agent_definition)
        image = definition.get("image", args.image)
        cpu = definition.get("cpu", args.cpu)
        memory = definition.get("memory", args.memory)
        env_vars = definition.get("environment_variables", {})
    else:
        image = args.image
        cpu = args.cpu
        memory = args.memory
        env_vars = {}
        for replacement in args.replacements:
            key, _, value = replacement.partition("=")
            if key and value:
                env_vars[key] = value

    if not image:
        print("ERROR: --image or image in --agent-definition must be provided.", file=sys.stderr)
        sys.exit(1)

    if not env_vars.get("AZURE_AI_PROJECT_ENDPOINT"):
        env_vars["AZURE_AI_PROJECT_ENDPOINT"] = project_endpoint

    print(f"Deploying hosted agent '{args.agent_name}'")
    print(f"  Image: {image}")
    print(f"  Endpoint: {project_endpoint}")

    # Create project client
    project = AIProjectClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential(),
        allow_preview=True,
    )

    # Create a hosted agent version
    agent = project.agents.create_version(
        agent_name=args.agent_name,
        definition=HostedAgentDefinition(
            container_protocol_versions=[
                ProtocolVersionRecord(protocol=AgentProtocol.RESPONSES, version="v1")
            ],
            cpu=cpu,
            memory=memory,
            image=image,
            environment_variables=env_vars,
        ),
    )

    print(f"Created hosted agent '{agent.name}', version: {agent.version}")
    print("Next step: verify status in the Foundry portal or run 'azd ai agent show'.")


if __name__ == "__main__":
    main()
