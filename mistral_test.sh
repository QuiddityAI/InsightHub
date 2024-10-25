export MISTRAL_API_KEY=3RfLPfVM6DAMCldkNZlMK0JFm3Rx1new

curl -X GET "https://api.mistral.ai/v1/models" \
  -H "Authorization: Bearer $MISTRAL_API_KEY" | python3 -m json.tool


{
    "object": "list",
    "data": [
        {
            "id": "ministral-3b-2410",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "ministral-3b-2410",
            "description": "Official ministral-3b-2410 Mistral AI model",
            "max_context_length": 32768,
            "aliases": [
                "ministral-3b-latest"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": false,
                "vision": false
            },
            "type": "base"
        },
        {
            "id": "ministral-3b-latest",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "ministral-3b-2410",
            "description": "Official ministral-3b-2410 Mistral AI model",
            "max_context_length": 32768,
            "aliases": [
                "ministral-3b-2410"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": false,
                "vision": false
            },
            "type": "base"
        },
        {
            "id": "ministral-8b-2410",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "ministral-8b-2410",
            "description": "Official ministral-8b-2410 Mistral AI model",
            "max_context_length": 32768,
            "aliases": [
                "ministral-8b-latest"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": false,
                "vision": false
            },
            "type": "base"
        },
        {
            "id": "ministral-8b-latest",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "ministral-8b-2410",
            "description": "Official ministral-8b-2410 Mistral AI model",
            "max_context_length": 32768,
            "aliases": [
                "ministral-8b-2410"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": false,
                "vision": false
            },
            "type": "base"
        },
        {
            "id": "open-mistral-7b",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "open-mistral-7b",
            "description": "Official open-mistral-7b Mistral AI model",
            "max_context_length": 32768,
            "aliases": [
                "mistral-tiny",
                "mistral-tiny-2312"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": true,
                "vision": false
            },
            "type": "base"
        },
        {
            "id": "mistral-tiny",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "open-mistral-7b",
            "description": "Official open-mistral-7b Mistral AI model",
            "max_context_length": 32768,
            "aliases": [
                "open-mistral-7b",
                "mistral-tiny-2312"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": true,
                "vision": false
            },
            "type": "base"
        },
        {
            "id": "mistral-tiny-2312",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "open-mistral-7b",
            "description": "Official open-mistral-7b Mistral AI model",
            "max_context_length": 32768,
            "aliases": [
                "open-mistral-7b",
                "mistral-tiny"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": true,
                "vision": false
            },
            "type": "base"
        },
        {
            "id": "open-mistral-nemo",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "open-mistral-nemo",
            "description": "Official open-mistral-nemo Mistral AI model",
            "max_context_length": 131072,
            "aliases": [
                "open-mistral-nemo-2407",
                "mistral-tiny-2407",
                "mistral-tiny-latest"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": true,
                "vision": false
            },
            "type": "base"
        },
        {
            "id": "open-mistral-nemo-2407",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "open-mistral-nemo",
            "description": "Official open-mistral-nemo Mistral AI model",
            "max_context_length": 131072,
            "aliases": [
                "open-mistral-nemo",
                "mistral-tiny-2407",
                "mistral-tiny-latest"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": true,
                "vision": false
            },
            "type": "base"
        },
        {
            "id": "mistral-tiny-2407",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "open-mistral-nemo",
            "description": "Official open-mistral-nemo Mistral AI model",
            "max_context_length": 131072,
            "aliases": [
                "open-mistral-nemo",
                "open-mistral-nemo-2407",
                "mistral-tiny-latest"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": true,
                "vision": false
            },
            "type": "base"
        },
        {
            "id": "mistral-tiny-latest",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "open-mistral-nemo",
            "description": "Official open-mistral-nemo Mistral AI model",
            "max_context_length": 131072,
            "aliases": [
                "open-mistral-nemo",
                "open-mistral-nemo-2407",
                "mistral-tiny-2407"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": true,
                "vision": false
            },
            "type": "base"
        },
        {
            "id": "open-mixtral-8x7b",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "open-mixtral-8x7b",
            "description": "Official open-mixtral-8x7b Mistral AI model",
            "max_context_length": 32768,
            "aliases": [
                "mistral-small",
                "mistral-small-2312"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": false,
                "vision": false
            },
            "type": "base"
        },
        {
            "id": "mistral-small",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "open-mixtral-8x7b",
            "description": "Official open-mixtral-8x7b Mistral AI model",
            "max_context_length": 32768,
            "aliases": [
                "open-mixtral-8x7b",
                "mistral-small-2312"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": false,
                "vision": false
            },
            "type": "base"
        },
        {
            "id": "mistral-small-2312",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "open-mixtral-8x7b",
            "description": "Official open-mixtral-8x7b Mistral AI model",
            "max_context_length": 32768,
            "aliases": [
                "open-mixtral-8x7b",
                "mistral-small"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": false,
                "vision": false
            },
            "type": "base"
        },
        {
            "id": "open-mixtral-8x22b",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "open-mixtral-8x22b",
            "description": "Official open-mixtral-8x22b Mistral AI model",
            "max_context_length": 65536,
            "aliases": [
                "open-mixtral-8x22b-2404"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": false,
                "vision": false
            },
            "type": "base"
        },
        {
            "id": "open-mixtral-8x22b-2404",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "open-mixtral-8x22b",
            "description": "Official open-mixtral-8x22b Mistral AI model",
            "max_context_length": 65536,
            "aliases": [
                "open-mixtral-8x22b"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": false,
                "vision": false
            },
            "type": "base"
        },
        {
            "id": "mistral-small-2402",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "mistral-small-2402",
            "description": "Official mistral-small-2402 Mistral AI model",
            "max_context_length": 32768,
            "aliases": [],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": true,
                "vision": false
            },
            "type": "base"
        },
        {
            "id": "mistral-small-2409",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "mistral-small-2409",
            "description": "Official mistral-small-2409 Mistral AI model",
            "max_context_length": 32768,
            "aliases": [
                "mistral-small-latest"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": false,
                "vision": false
            },
            "type": "base"
        },
        {
            "id": "mistral-small-latest",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "mistral-small-2409",
            "description": "Official mistral-small-2409 Mistral AI model",
            "max_context_length": 32768,
            "aliases": [
                "mistral-small-2409"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": false,
                "vision": false
            },
            "type": "base"
        },
        {
            "id": "mistral-medium-2312",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "mistral-medium-2312",
            "description": "Official mistral-medium-2312 Mistral AI model",
            "max_context_length": 32768,
            "aliases": [
                "mistral-medium",
                "mistral-medium-latest"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": false,
                "vision": false
            },
            "type": "base"
        },
        {
            "id": "mistral-medium",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "mistral-medium-2312",
            "description": "Official mistral-medium-2312 Mistral AI model",
            "max_context_length": 32768,
            "aliases": [
                "mistral-medium-2312",
                "mistral-medium-latest"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": false,
                "vision": false
            },
            "type": "base"
        },
        {
            "id": "mistral-medium-latest",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "mistral-medium-2312",
            "description": "Official mistral-medium-2312 Mistral AI model",
            "max_context_length": 32768,
            "aliases": [
                "mistral-medium-2312",
                "mistral-medium"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": false,
                "vision": false
            },
            "type": "base"
        },
        {
            "id": "mistral-large-2402",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "mistral-large-2402",
            "description": "Official mistral-large-2402 Mistral AI model",
            "max_context_length": 32768,
            "aliases": [],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": false,
                "vision": false
            },
            "type": "base"
        },
        {
            "id": "mistral-large-2407",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "mistral-large-2407",
            "description": "Official mistral-large-2407 Mistral AI model",
            "max_context_length": 131072,
            "aliases": [
                "mistral-large-latest"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": true,
                "vision": false
            },
            "type": "base"
        },
        {
            "id": "mistral-large-latest",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "mistral-large-2407",
            "description": "Official mistral-large-2407 Mistral AI model",
            "max_context_length": 131072,
            "aliases": [
                "mistral-large-2407"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": true,
                "vision": false
            },
            "type": "base"
        },
        {
            "id": "codestral-2405",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "codestral-2405",
            "description": "Official codestral-2405 Mistral AI model",
            "max_context_length": 32768,
            "aliases": [
                "codestral-latest"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": true,
                "function_calling": true,
                "fine_tuning": true,
                "vision": false
            },
            "type": "base"
        },
        {
            "id": "codestral-latest",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "codestral-2405",
            "description": "Official codestral-2405 Mistral AI model",
            "max_context_length": 32768,
            "aliases": [
                "codestral-2405"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": true,
                "function_calling": true,
                "fine_tuning": true,
                "vision": false
            },
            "type": "base"
        },
        {
            "id": "codestral-mamba-2407",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "codestral-mamba-2407",
            "description": "Official codestral-mamba-2407 Mistral AI model",
            "max_context_length": 32768,
            "aliases": [
                "open-codestral-mamba",
                "codestral-mamba-latest"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": false,
                "vision": false
            },
            "type": "base"
        },
        {
            "id": "open-codestral-mamba",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "codestral-mamba-2407",
            "description": "Official codestral-mamba-2407 Mistral AI model",
            "max_context_length": 32768,
            "aliases": [
                "codestral-mamba-2407",
                "codestral-mamba-latest"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": false,
                "vision": false
            },
            "type": "base"
        },
        {
            "id": "codestral-mamba-latest",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "codestral-mamba-2407",
            "description": "Official codestral-mamba-2407 Mistral AI model",
            "max_context_length": 32768,
            "aliases": [
                "codestral-mamba-2407",
                "open-codestral-mamba"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": false,
                "vision": false
            },
            "type": "base"
        },
        {
            "id": "pixtral-12b-2409",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "pixtral-12b-2409",
            "description": "Official pixtral-12b-2409 Mistral AI model",
            "max_context_length": 131072,
            "aliases": [
                "pixtral-12b",
                "pixtral-12b-latest"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": false,
                "vision": true
            },
            "type": "base"
        },
        {
            "id": "pixtral-12b",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "pixtral-12b-2409",
            "description": "Official pixtral-12b-2409 Mistral AI model",
            "max_context_length": 131072,
            "aliases": [
                "pixtral-12b-2409",
                "pixtral-12b-latest"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": false,
                "vision": true
            },
            "type": "base"
        },
        {
            "id": "pixtral-12b-latest",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "pixtral-12b-2409",
            "description": "Official pixtral-12b-2409 Mistral AI model",
            "max_context_length": 131072,
            "aliases": [
                "pixtral-12b-2409",
                "pixtral-12b"
            ],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": false,
                "vision": true
            },
            "type": "base"
        },
        {
            "id": "mistral-embed",
            "object": "model",
            "created": 1729540029,
            "owned_by": "mistralai",
            "name": "mistral-embed",
            "description": "Official mistral-embed Mistral AI model",
            "max_context_length": 32768,
            "aliases": [],
            "deprecation": null,
            "capabilities": {
                "completion_chat": true,
                "completion_fim": false,
                "function_calling": true,
                "fine_tuning": false,
                "vision": false
            },
            "type": "base"
        }
    ]
}