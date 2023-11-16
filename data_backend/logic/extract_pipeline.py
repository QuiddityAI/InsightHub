import json
import logging
from typing import Callable, Optional

from utils.dotdict import DotDict
from logic.generator_functions import get_generator_function_from_field


# TODO: add changed_at as parameter and cache function (using changed_at as measure for dropping the cache)
def get_pipeline_steps(dataset_: dict, ignored_fields: list[str] = [], enabled_fields: list[str] = [], only_fields: list[str] = []) -> tuple[list[list[dict]], set[str], set[str]]:
    dataset: DotDict = DotDict(dataset_)
    if has_circular_dependency(dataset):
        logging.error(f"The pipeline steps have a circular dependency, object dataset: {dataset.name}")
        logging.error(f"No pipeline steps will be executed at all for this dataset until this is fixed.")
        return [], set(), set()

    required_fields: set[str] = set()
    potentially_changed_fields: set[str] = set()
    pipeline_steps: list[list[dict]] = []
    steps_added: list[str] = []
    any_field_skipped: bool = True
    while any_field_skipped:
        phase_steps: list[dict] = []
        steps_added_this_phase: list[str] = []
        any_field_skipped = False
        for field in dataset.object_fields.values():
            if field.identifier in steps_added: continue
            this_field_skipped: bool = False

            if ((not only_fields and field.should_be_generated and not field.identifier in ignored_fields)
                    or field.identifier in only_fields
                    or field.identifier in enabled_fields):
                dependencies: list[str] = field.source_fields
                for dep in dependencies:
                    if dataset.object_fields[dep].generator and dep not in steps_added:
                        this_field_skipped = True
                        enabled_fields.append(dep)
                        break
                if this_field_skipped:
                    any_field_skipped = True
                    continue

                generator_function: Callable = get_generator_function_from_field(field)
                condition_function: Optional[Callable] = eval(field.generating_condition) if field.generating_condition else None

                required_fields |= set(field.source_fields)
                potentially_changed_fields.add(field.identifier)
                phase_steps.append({
                    'source_fields': field.source_fields,
                    'generator_function': generator_function,
                    'condition_function': condition_function,
                    'target_field': field.identifier,
                })
                steps_added_this_phase.append(field.identifier)
        if phase_steps:
            pipeline_steps.append(phase_steps)
            steps_added += steps_added_this_phase

    return pipeline_steps, required_fields, potentially_changed_fields


def has_circular_dependency(dataset: dict) -> bool:
    dataset = DotDict(dataset)
    steps_added = []
    any_field_skipped = True
    any_field_added = True  # used to prevent endless loop with circular dependencies
    while any_field_skipped and any_field_added:
        steps_added_this_phase = []
        any_field_skipped = False
        any_field_added = False
        for field in dataset.object_fields.values():
            if field.identifier in steps_added: continue
            this_field_skipped = False
            dependencies = field.source_fields
            for dep in dependencies:
                if dep not in steps_added:
                    this_field_skipped = True
                    break
            if this_field_skipped:
                any_field_skipped = True
                continue
            steps_added_this_phase.append(field.identifier)
            any_field_added = True
        if steps_added_this_phase:
            steps_added += steps_added_this_phase
        if not any_field_added and any_field_skipped:
            # -> circular dependency
            return True
    return False

