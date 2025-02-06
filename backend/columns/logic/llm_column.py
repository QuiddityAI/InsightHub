from django.utils import timezone
from llmonkey.llms import BaseLLMModel

from data_map_backend.models import CollectionColumn, ServiceUsage
from config.utils import get_default_model
from columns.schemas import CellData, Criterion
import dspy


class RelevanceSignature(dspy.Signature):
    """You are a helpful assistant for evaluating the relevance of a document based on a list of criteria."""

    document: str = dspy.InputField()
    criterion: str = dspy.InputField()
    target_language: str = dspy.InputField(desc="The desired output language for reason")
    fullfilled: bool = dspy.OutputField()
    reason: str = dspy.OutputField(
        desc="Very short explanation of why the criterion is fulfilled or not (in output_language)"
    )
    supporting_quote: str = dspy.OutputField(
        desc="Short quote from the document explaining the criterion in original language"
    )


class RelevanceJudge(dspy.Module):
    def __init__(self, callbacks=None):
        super().__init__(callbacks)
        self.relevance = dspy.Predict(RelevanceSignature)

    def forward(self, document: str, criteria: list[str], target_language: str) -> list[Criterion]:
        criteria_review = []
        for c in criteria:
            rel = self.relevance(document=document, criterion=c, target_language=target_language)
            criteria_review.append(
                Criterion(
                    criteria=c, fulfilled=rel.fullfilled, reason=rel.reason, supporting_quote=rel.supporting_quote
                )
            )

        return criteria_review


class CellPromptSignature(dspy.Signature):
    """You are a helpful assistant, helping user to extract information from a document.
    The answers will be stored in the table column, named column_title.
    Given the user prompt, you will generate a short answer based on the document.
    Answer in the language given as the target_language.
    Follow the rules for the answer format:
        - If not stated otherwise, answer in one concise sentence, word or list.
        - Keep the answer close to the document's wording.
        - Only use information that is directly stated in the document.
        - If the document does not contain the answer, answer with 'n/a'.
        - If the answer is unclear, answer with '?'.
        - Use markdown to format your answer.
        - In long sentences, highlight important words or phrases using two asterisks.
        - Write chemical and math formulas using LaTeX math syntax and wrap them in dollar signs.
          For example, a math expression like e = mc^2 should be written as $e = mc^2$.
        - Do not use any headings.
    """

    document: str = dspy.InputField()
    column_title: str = dspy.InputField()
    target_language: str = dspy.InputField()
    user_prompt: str = dspy.InputField()
    output: str = dspy.OutputField()


class CellPromptExecutor(dspy.Module):
    def __init__(self, callbacks=None):
        super().__init__(callbacks)
        self.predictor = dspy.Predict(CellPromptSignature)

    def forward(self, document: str, column_title: str, target_language: str, user_prompt: str) -> str:
        out = self.predictor(
            document=document, column_title=column_title, target_language=target_language, user_prompt=user_prompt
        )
        return out.output


def generate_custom_prompt_response(
    column: CollectionColumn, model: BaseLLMModel, input_data: str, user_prompt: str = None
) -> tuple[str, str]:
    """Handler for generating a custom prompt response for a column using direct call to the model."""
    system_prompt = column.prompt_template
    replacements = [
        ("title", column.name),
        ("expression", column.expression or ""),
        ("document", input_data.strip()),
    ]
    for key, value in replacements:
        system_prompt = system_prompt.replace("{{ " + key + " }}", value)

    response = model.generate_prompt_response(
        system_prompt=system_prompt,
        user_prompt=user_prompt or "",
        max_tokens=2000,
    )
    return response.conversation[-1].content, system_prompt


def generate_llm_cell_data(
    input_data: str, column: CollectionColumn, user_id: int, is_relevance_column: bool = False
) -> CellData:
    default_model = get_default_model("medium").__class__.__name__
    model_name = column.parameters.get("model") or default_model

    cell_data = CellData(
        changed_at=timezone.now().isoformat(),
        is_ai_generated=True,
        is_computed=True,
        is_manually_edited=False,
        used_llm_model=model_name,
    )
    # if not column.parameters.get("model"):
    #     logging.error("No model specified for LLM column.")
    #     cell_data["value"] = "No model specified"
    #     return cell_data
    model = BaseLLMModel.load(model_name)

    # necessary 'AI credits' is defined by us as the cost per 1M tokens / factor:
    ai_credits = model.config.euro_per_1M_output_tokens / 5.0
    usage_tracker = ServiceUsage.get_usage_tracker(user_id, "External AI")
    result = usage_tracker.track_usage(ai_credits, f"extract information using {model.__class__.__name__}")
    if result["approved"] != True:
        cell_data.value = "AI usage limit exceeded"
        return cell_data

    if is_relevance_column:
        # handle special case for relevance column
        language = column.parameters.get("language") or "en"
        judge = RelevanceJudge()
        criteria = column.expression.split("\n")
        with dspy.context(lm=dspy.LM(**model.to_litellm())):
            criteria_review = judge(document=input_data, criteria=criteria, target_language=language)
        relevance_score = sum([c.fulfilled for c in criteria_review]) / max(len(criteria_review), 1)
        value = {
            "criteria_review": [c.model_dump() for c in criteria_review],  # type: ignore
            "is_relevant": relevance_score > 0.6,
            "relevance_score": relevance_score,
        }
        cell_data.value = value
        cell_data.used_prompt = f"system_prompt: {judge.__class__.__name__}"
        return cell_data

    if column.prompt_template:
        # if the column has a prompt template, we use it to generate the system prompt
        value, used_prompt = generate_custom_prompt_response(column, model, input_data)
        cell_data.value = value
        cell_data.used_prompt = f"system_prompt:\n{used_prompt}"
        return cell_data
    else:
        # otherwise we use the default DSPy module to generate the response
        language = column.parameters.get("language") or "en"
        executor = CellPromptExecutor()
        with dspy.context(lm=dspy.LM(**model.to_litellm())):
            value = executor(
                document=input_data.strip(),
                column_title=column.name,
                target_language=language,
                user_prompt=column.expression,
            )
        cell_data.value = value
        cell_data.used_prompt = f"system_prompt: {executor.__class__.__name__}"
        return cell_data
