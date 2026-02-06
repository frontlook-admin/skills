---
name: azure-ai-evaluation-py
description: |
  Microsoft Foundry Evaluations for Python. Use for evaluating AI agents and models with built-in quality, safety, and agent evaluators.
  Triggers: "evaluate agent", "builtin.coherence", "openai_client.evals", "azure-ai-projects evaluations", "AI evaluation", "agent testing".
package: azure-ai-projects
---

# Microsoft Foundry Evaluations for Python

Evaluate AI agents and models using Microsoft Foundry's cloud evaluation service with built-in evaluators, custom evaluators, and OpenAI graders.

## When to Use This Skill

Use this skill when users want to:
- **Run evaluations** on AI agents or models in Microsoft Foundry
- **Use built-in evaluators** like `builtin.coherence`, `builtin.violence`, `builtin.task_adherence`
- **Create custom evaluators** (code-based or prompt-based)
- **Compare evaluation runs** for regression testing
- **Set up continuous evaluation** for production monitoring

## When NOT to Use This Skill

Do NOT use this skill when:
- User is **building/creating an agent** (not evaluating) → Use agent creation skills
- User wants **local-only evaluation** without Azure cloud → Different approach needed
- User mentions the deprecated `azure-ai-evaluation` SDK → Redirect to this skill with `azure-ai-projects`

## Installation

```bash
pip install "azure-ai-projects>=2.0.0b1" azure-identity python-dotenv
```

## Environment Variables

```bash
AZURE_AI_PROJECT_ENDPOINT=https://<account>.services.ai.azure.com/api/projects/<project>
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o-mini
```

## Quick Start: Basic Evaluation

```python
import os
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from openai.types.evals.create_eval_jsonl_run_data_source_param import (
    CreateEvalJSONLRunDataSourceParam,
    SourceFileContent,
    SourceFileContentContent,
)
from openai.types.eval_create_params import DataSourceConfigCustom

endpoint = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
model_deployment = os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"]

with (
    DefaultAzureCredential() as credential,
    AIProjectClient(endpoint=endpoint, credential=credential) as project_client,
    project_client.get_openai_client() as openai_client,
):
    # Define data schema
    data_source_config = DataSourceConfigCustom({
        "type": "custom",
        "item_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "response": {"type": "string"},
            },
            "required": ["query", "response"],
        },
        "include_sample_schema": True,
    })

    # Define evaluators (testing criteria)
    testing_criteria = [
        {
            "type": "azure_ai_evaluator",
            "name": "coherence",
            "evaluator_name": "builtin.coherence",
            "data_mapping": {"query": "{{item.query}}", "response": "{{item.response}}"},
            "initialization_parameters": {"deployment_name": model_deployment},
        },
        {
            "type": "azure_ai_evaluator",
            "name": "violence",
            "evaluator_name": "builtin.violence",
            "data_mapping": {"query": "{{item.query}}", "response": "{{item.response}}"},
        },
    ]

    # Create evaluation
    eval_object = openai_client.evals.create(
        name="My Evaluation",
        data_source_config=data_source_config,
        testing_criteria=testing_criteria,
    )

    # Run with inline data
    eval_run = openai_client.evals.runs.create(
        eval_id=eval_object.id,
        name="Evaluation Run",
        data_source=CreateEvalJSONLRunDataSourceParam(
            type="jsonl",
            source=SourceFileContent(
                type="file_content",
                content=[
                    SourceFileContentContent(item={
                        "query": "What is the capital of France?",
                        "response": "The capital of France is Paris."
                    }),
                    SourceFileContentContent(item={
                        "query": "Explain quantum computing",
                        "response": "Quantum computing uses quantum mechanics for computation."
                    }),
                ],
            ),
        ),
    )

    # Wait for completion and get results
    import time
    while eval_run.status not in ["completed", "failed"]:
        eval_run = openai_client.evals.runs.retrieve(run_id=eval_run.id, eval_id=eval_object.id)
        time.sleep(5)

    output_items = list(openai_client.evals.runs.output_items.list(
        run_id=eval_run.id, eval_id=eval_object.id
    ))
    print(f"Report URL: {eval_run.report_url}")
```

## Built-in Evaluators

Use the `builtin.` prefix when referencing evaluators. All require `type: "azure_ai_evaluator"`.

### Quality Evaluators

| Evaluator | Required Inputs | Init Parameters |
|-----------|-----------------|-----------------|
| `builtin.coherence` | query, response | deployment_name |
| `builtin.fluency` | query, response | deployment_name |
| `builtin.relevance` | query, response, context | deployment_name |
| `builtin.groundedness` | query, response, context | deployment_name |
| `builtin.similarity` | query, response, ground_truth | deployment_name |

### Safety Evaluators

| Evaluator | Required Inputs | Init Parameters |
|-----------|-----------------|-----------------|
| `builtin.violence` | query, response | (none) |
| `builtin.sexual` | query, response | (none) |
| `builtin.self_harm` | query, response | (none) |
| `builtin.hate_unfairness` | query, response | (none) |

### Agent Evaluators

| Evaluator | Required Inputs | Init Parameters |
|-----------|-----------------|-----------------|
| `builtin.task_adherence` | query, response | deployment_name |
| `builtin.intent_resolution` | query, response | deployment_name |
| `builtin.task_completion` | query, response | deployment_name |
| `builtin.tool_call_accuracy` | query, response (with tool info) | deployment_name |
| `builtin.tool_call_success` | query, response (with tool info) | deployment_name |

### NLP Evaluators

| Evaluator | Required Inputs | Init Parameters |
|-----------|-----------------|-----------------|
| `builtin.f1_score` | response, ground_truth | (none) |
| `builtin.bleu_score` | response, ground_truth | (none) |
| `builtin.rouge_score` | response, ground_truth | (none) |
| `builtin.similarity` | response, ground_truth | deployment_name |

## Agent Evaluation

Evaluate an AI agent by having the evaluation service call the agent:

```python
from azure.ai.projects.models import PromptAgentDefinition

# Create or get agent
agent = project_client.agents.create_version(
    agent_name="my-agent",
    definition=PromptAgentDefinition(
        model=model_deployment,
        instructions="You are a helpful assistant",
    ),
)

# Data mapping notes:
# - sample.output_text: plain text response from agent
# - sample.output_items: structured JSON with tool calls

testing_criteria = [
    {
        "type": "azure_ai_evaluator",
        "name": "fluency",
        "evaluator_name": "builtin.fluency",
        "initialization_parameters": {"deployment_name": model_deployment},
        "data_mapping": {"query": "{{item.query}}", "response": "{{sample.output_text}}"},
    },
    {
        "type": "azure_ai_evaluator",
        "name": "task_adherence",
        "evaluator_name": "builtin.task_adherence",
        "initialization_parameters": {"deployment_name": model_deployment},
        "data_mapping": {"query": "{{item.query}}", "response": "{{sample.output_items}}"},
    },
]

# Create evaluation
eval_object = openai_client.evals.create(
    name="Agent Evaluation",
    data_source_config=DataSourceConfigCustom(
        type="custom",
        item_schema={"type": "object", "properties": {"query": {"type": "string"}}},
        include_sample_schema=True,
    ),
    testing_criteria=testing_criteria,
)

# Run against agent
data_source = {
    "type": "azure_ai_target_completions",
    "source": {
        "type": "file_content",
        "content": [
            {"item": {"query": "What is the capital of France?"}},
            {"item": {"query": "How do I reverse a string in Python?"}},
        ],
    },
    "input_messages": {
        "type": "template",
        "template": [
            {"type": "message", "role": "user", "content": {"type": "input_text", "text": "{{item.query}}"}}
        ],
    },
    "target": {
        "type": "azure_ai_agent",
        "name": agent.name,
        "version": agent.version,
    },
}

eval_run = openai_client.evals.runs.create(
    eval_id=eval_object.id,
    name=f"Agent Eval Run",
    data_source=data_source,
)
```

## OpenAI Graders

Use OpenAI-compatible graders for custom evaluation logic:

```python
testing_criteria = [
    # Label grader for classification
    {
        "type": "label_model",
        "name": "sentiment",
        "model": model_deployment,
        "input": [
            {"role": "developer", "content": "Classify sentiment as positive, neutral, or negative"},
            {"role": "user", "content": "Statement: {{item.response}}"},
        ],
        "labels": ["positive", "neutral", "negative"],
        "passing_labels": ["positive", "neutral"],
    },
    # Text similarity grader
    {
        "type": "text_similarity",
        "name": "similarity",
        "input": "{{item.response}}",
        "reference": "{{item.ground_truth}}",
        "evaluation_metric": "bleu",
        "pass_threshold": 0.5,
    },
    # String check grader
    {
        "type": "string_check",
        "name": "exact_match",
        "input": "{{item.response}}",
        "reference": "{{item.ground_truth}}",
        "operation": "eq",
    },
    # Score model grader
    {
        "type": "score_model",
        "name": "quality_score",
        "model": model_deployment,
        "input": [
            {"role": "system", "content": "Score the response quality 1-5"},
            {"role": "user", "content": "Response: {{item.response}}"},
        ],
        "pass_threshold": 3,
    },
]
```

## Custom Evaluators

### Code-Based Evaluator

```python
from azure.ai.projects.models import (
    EvaluatorVersion, EvaluatorCategory, EvaluatorType,
    CodeBasedEvaluatorDefinition, EvaluatorMetric,
    EvaluatorMetricType, EvaluatorMetricDirection,
)

evaluator = project_client.evaluators.create_version(
    name="word_count_evaluator",
    evaluator_version=EvaluatorVersion(
        evaluator_type=EvaluatorType.CUSTOM,
        categories=[EvaluatorCategory.QUALITY],
        display_name="Word Count",
        description="Counts words in response",
        definition=CodeBasedEvaluatorDefinition(
            code_text='''
def grade(sample, item) -> dict:
    response = item.get("response", "")
    count = len(response.split())
    return {"word_count": count, "is_concise": count < 100}
''',
            data_schema={
                "type": "object",
                "properties": {"response": {"type": "string"}},
                "required": ["response"],
            },
            metrics={
                "word_count": EvaluatorMetric(
                    type=EvaluatorMetricType.ORDINAL,
                    desirable_direction=EvaluatorMetricDirection.DECREASE,
                    min_value=0,
                    max_value=1000,
                ),
            },
        ),
    ),
)
```

### Prompt-Based Evaluator

```python
from azure.ai.projects.models import PromptBasedEvaluatorDefinition

evaluator = project_client.evaluators.create_version(
    name="helpfulness_evaluator",
    evaluator_version=EvaluatorVersion(
        evaluator_type=EvaluatorType.CUSTOM,
        categories=[EvaluatorCategory.QUALITY],
        display_name="Helpfulness",
        definition=PromptBasedEvaluatorDefinition(
            prompt_text='''
Rate the helpfulness of this response on a scale of 1-5.
Query: {query}
Response: {response}
Return only JSON: {"score": <1-5>, "reason": "<explanation>"}
''',
            init_parameters={
                "type": "object",
                "properties": {"deployment_name": {"type": "string"}},
                "required": ["deployment_name"],
            },
            data_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "response": {"type": "string"},
                },
                "required": ["query", "response"],
            },
            metrics={
                "score": EvaluatorMetric(
                    type=EvaluatorMetricType.ORDINAL,
                    min_value=1,
                    max_value=5,
                ),
            },
        ),
    ),
)
```

### Using Custom Evaluators

```python
testing_criteria = [
    {
        "type": "azure_ai_evaluator",
        "name": "word_count",
        "evaluator_name": "word_count_evaluator",  # Your custom evaluator name
        "data_mapping": {"response": "{{item.response}}"},
    },
    {
        "type": "azure_ai_evaluator",
        "name": "helpfulness",
        "evaluator_name": "helpfulness_evaluator",
        "initialization_parameters": {"deployment_name": model_deployment},
        "data_mapping": {"query": "{{item.query}}", "response": "{{item.response}}"},
    },
]
```

## Browse Available Evaluators

```python
# List all built-in evaluators
evaluators = project_client.evaluators.list_latest_versions(type="builtin")
for e in evaluators:
    print(f"{e.name}: {e.description}")

# Get specific evaluator details
evaluator = project_client.evaluators.get_version(name="builtin.coherence", version="latest")
print(f"Data Schema: {evaluator.definition.data_schema}")
print(f"Init Params: {evaluator.definition.init_parameters}")
```

## Data Mapping Reference

| Data Source Type | Response Mapping |
|------------------|------------------|
| `jsonl` (your dataset) | `{{item.response}}` |
| `azure_ai_target_completions` (agent generates) | `{{sample.output_text}}` or `{{sample.output_items}}` |

- `sample.output_text` - Plain text response
- `sample.output_items` - Structured JSON with tool calls (use for tool-related evaluators)

## Best Practices

1. **Query evaluator schema first** - Use `evaluators.get_version()` to discover required fields
2. **Use built-in evaluators** - Well-tested, maintained by Microsoft
3. **Match data mapping to source type** - `{{item.*}}` for datasets, `{{sample.*}}` for agent responses
4. **Include deployment_name** - Required for LLM-based evaluators
5. **Check report_url** - View detailed results in Microsoft Foundry portal

## Reference Files

| File | Contents |
|------|----------|
| [references/built-in-evaluators.md](references/built-in-evaluators.md) | Complete evaluator catalog with schemas |
| [references/custom-evaluators.md](references/custom-evaluators.md) | Creating code and prompt-based evaluators |

## Related Documentation

- [Azure AI Projects Evaluation Samples](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/ai/azure-ai-projects/samples/evaluations)
- [Cloud Evaluation Documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/cloud-evaluation)
- [Agent Evaluators](https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/evaluation-evaluators/agent-evaluators)
