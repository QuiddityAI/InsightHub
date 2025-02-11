<script setup>
import { ref, computed, watch, inject } from 'vue';
import { useToast } from 'primevue/usetoast';
import MultiSelect from 'primevue/multiselect';
import Message from 'primevue/message';
import Checkbox from 'primevue/checkbox';
import { useI18n } from 'vue-i18n';

import LanguageSelect from "../widgets/LanguageSelect.vue"
import BorderButton from "../widgets/BorderButton.vue"
import LlmSelect from '../widgets/LlmSelect.vue';

import { httpClient } from "../../api/httpClient"
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { useCollectionStore } from "../../stores/collection_store"
import { FieldType } from "../../utils/utils"

// Props and emits
const props = defineProps(['collection', 'collection_class'])
const emit = defineEmits(['close'])

// Store initialization
const appState = useAppStateStore()
const mapState = useMapStateStore()
const collectionStore = useCollectionStore()
const toast = useToast()
const eventBus = inject('eventBus')

// Reactive state
const selected_source_fields = ref(['_descriptive_text_fields', '_full_text_snippets'])
const selected_module = ref('llm')
const selected_llm = ref('Google_Gemini_Flash_1_5_v1')
const selected_language = ref(null)
const show_advanced_modules = ref(false)
const use_auto_title = ref(true)
const use_auto_prompt = ref(true)
const use_auto_language = ref(true)
const use_custom_llm = ref(false)
const use_default_sources = ref(true)
const auto_run_for_approved_items = ref(false)
const auto_run_for_candidates = ref(false)
const title = ref('')
const expression = ref('')
const custom_prompt = ref('')

const { t } = useI18n();

// Constants
const default_models = [
  { 'title': t('AddColumnDialog.small-ai'), 'subtitle': t('AddColumnDialog.small-ai-subtitle'), 'model': 'Mistral_Ministral8b' },
  { 'title': t('AddColumnDialog.medium-ai'), 'subtitle': t('AddColumnDialog.medium-ai-subtitle'), 'model': 'Google_Gemini_Flash_1_5_v1' },
  { 'title': t('AddColumnDialog.large-ai'), 'subtitle': t('AddColumnDialog.large-ai-subtitle'), 'model': 'Mistral_Mistral_Large' },
]

// Computed properties
const show_full_text_issue_hint = computed(() => {
  return selected_source_fields.value.find((field) => field !== "_full_text_snippets" && field.includes("full_text"))
})

const expression_label = computed(() => {
  if (selected_module.value === 'llm') {
    return t('AddColumnDialog.expression-label-llm')
  } else if (selected_module.value === 'relevance') {
    return t('AddColumnDialog.expression-label-relevance')
  } else if (selected_module.value === 'email') {
    return t('AddColumnDialog.expression-label-email')
  } else {
    return t('AddColumnDialog.expression-label-other')
  }
})

const sources_label = computed(() => {
  if (selected_module.value === 'llm' || selected_module.value === 'relevance') {
    return t('AddColumnDialog.sources-label-llm')
  } else if (selected_module.value === 'website_scraping') {
    return t('AddColumnDialog.sources-label-url')
  } else if (selected_module.value === 'web_search') {
    return t('AddColumnDialog.sources-label-web-search')
  } else if (selected_module.value === 'item_field') {
    return t('AddColumnDialog.sources-label-item-field')
  } else {
    return t('AddColumnDialog.sources-label-other')
  }
})

const prompt_label = computed(() => {
  if (selected_module.value === 'llm') {
    return t('AddColumnDialog.prompt-label-llm')
  } else if (selected_module.value === 'email') {
    return t('AddColumnDialog.prompt-label-email')
  } else {
    return t('AddColumnDialog.prompt-label-other')
  }
})

const show_process_now_button = computed(() => {
  return !['email', 'notes'].includes(selected_module.value)
})

const show_add_without_processing_button = computed(() => {
  return !['item_field'].includes(selected_module.value)
})

// Methods
const set_default_values = () => {
  use_auto_title.value = true
  use_auto_prompt.value = true
  use_auto_language.value = true
  auto_run_for_approved_items.value = false
  auto_run_for_candidates.value = false
  use_default_sources.value = true

  if (selected_module.value === 'llm') {
    // Default values already set
  } else if (selected_module.value === 'relevance') {
    auto_run_for_candidates.value = true
  } else if (selected_module.value === 'website_scraping') {
    use_default_sources.value = false
  } else if (selected_module.value === 'web_search') {
    use_default_sources.value = false
  } else if (selected_module.value === 'item_field') {
    use_default_sources.value = false
    auto_run_for_candidates.value = true
    auto_run_for_approved_items.value = true
    use_auto_title.value = true
  } else if (selected_module.value === 'email') {
    use_auto_language.value = false
    selected_language.value = 'en'
  } else if (selected_module.value === 'notes') {
    auto_run_for_candidates.value = false
    auto_run_for_approved_items.value = false
  }

  if (['item_field', 'web_search', 'website_scraping'].includes(selected_module.value)) {
    selected_source_fields.value = []
  } else {
    selected_source_fields.value = ['_descriptive_text_fields', '_full_text_snippets']
  }
}

const add_extraction_question = (process_current_page = false) => {
  const parameters = {}
  if (['llm', 'relevance', 'email'].includes(selected_module.value)) {
    parameters.model = selected_llm.value
    parameters.language = selected_language.value
  }

  let field_type = FieldType.TEXT
  if (['relevance'].includes(selected_module.value)) {
    field_type = FieldType.ARBITRARY_OBJECT
  }

  const body = {
    collection_id: collectionStore.collection_id,
    field_type: field_type,
    name: title.value,
    expression: expression.value,
    source_fields: selected_source_fields.value,
    module: selected_module.value,
    prompt_template: custom_prompt.value,
    auto_run_for_approved_items: auto_run_for_approved_items.value,
    auto_run_for_candidates: auto_run_for_candidates.value,
    parameters: parameters,
  }

  httpClient.post(`/api/v1/columns/add_column`, body)
    .then((response) => {
      if (!props.collection.columns) {
        props.collection.columns = []
      }
      const column = response.data
      props.collection.columns.push(column)
      if (process_current_page) {
        collectionStore.extract_question(column.id, true)
      }
    })
    .catch((error) => {
      console.error(error)
    })
  emit('close')
}

// Watchers
watch(use_auto_title, (value) => {
  if (value) {
    title.value = ''
  }
})

watch(use_auto_language, (value) => {
  if (value) {
    selected_language.value = null
  }
})

watch(use_auto_prompt, (value) => {
  if (value) {
    custom_prompt.value = ''
  }
})

watch(selected_module, () => {
  set_default_values()
})
</script>

<template>
  <div class="flex flex-col gap-3">

    <div class="flex flex-row items-center gap-2 flex-wrap">
      <BorderButton v-for="module in appState.column_modules.filter(module => module.highlight)"
        @click="selected_module = module.identifier"
        :highlighted="selected_module === module.identifier">
        {{ $t(module.name) }}
      </BorderButton>
      <BorderButton v-tooltip.top="{ value: $t('AddColumnDialog.show-advanced-modules') }"
        @click="show_advanced_modules = !show_advanced_modules"
        :highlighted="show_advanced_modules">
        ...
      </BorderButton>
    </div>
    <div class="flex flex-row items-center gap-2 flex-wrap" v-if="show_advanced_modules">
      <BorderButton v-for="module in appState.column_modules.filter(module => !module.highlight)"
        @click="selected_module = module.identifier"
        :highlighted="selected_module === module.identifier">
        {{ $t(module.name) }}
      </BorderButton>
    </div>
    <div class="text-xs text-gray-500">
      {{ $t(appState.column_modules.find(module => module.identifier === selected_module).help_text) }}
    </div>

    <div class="flex flex-row items-center mb-4 mt-4" v-if="['llm', 'relevance', 'email'].includes(selected_module)">
      <textarea type="text" v-model="expression"
        class="flex-auto rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
        :placeholder="expression_label" />
      <LanguageSelect v-if="!use_auto_language"
        :available_language_codes="['en', 'de']"
        v-model="selected_language"
        :offer_wildcard="true" :use_last_used_language="false"
        :tooltip="$t('AddColumnDialog.language-tooltip')">
      </LanguageSelect>
    </div>

    <div class="flex flex-row gap-5 items-center">
      <div class="flex flex-row items-center"
        v-tooltip.top="{ value: $t('AddColumnDialog.auto-title-tooltip') }">
        <Checkbox v-model="use_auto_title" :binary="true" />
        <button class="ml-2 text-xs text-gray-500"
          @click="use_auto_title = !use_auto_title">
          {{ $t('AddColumnDialog.auto-title') }}
        </button>
      </div>
      <div class="flex flex-row items-center" v-if="['llm', 'relevance'].includes(selected_module)"
        v-tooltip.top="{ value: $t('AddColumnDialog.auto-language-tooltip') }">
        <Checkbox v-model="use_auto_language" :binary="true" />
        <button class="ml-2 text-xs text-gray-500"
          @click="use_auto_language = !use_auto_language">
          {{ $t('AddColumnDialog.auto-language') }}
        </button>
      </div>
      <div class="flex flex-row items-center" v-if="['llm', 'email'].includes(selected_module)"
        v-tooltip.top="{ value: $t('AddColumnDialog.default-prompt-tooltip') }">
        <Checkbox v-model="use_auto_prompt" :binary="true" />
        <button class="ml-2 text-xs text-gray-500"
          @click="use_auto_prompt = !use_auto_prompt">
          {{ selected_module == 'email' ? $t('AddColumnDialog.default-email-template') : $t('AddColumnDialog.auto-prompt') }}
        </button>
      </div>
      <div class="flex flex-row items-center" v-if="['llm', 'relevance', 'email'].includes(selected_module)"
        v-tooltip.top="{ value: $t('AddColumnDialog.default-sources-tooltip') }">
        <Checkbox v-model="use_default_sources" :binary="true" />
        <button class="ml-2 text-xs text-gray-500"
          @click="use_default_sources = !use_default_sources">
          {{ $t('AddColumnDialog.default-sources') }}
        </button>
      </div>
    </div>

    <div class="flex flex-row gap-5 items-center" v-if="!['notes', 'item_field'].includes(selected_module)">
      <div class="flex flex-row items-center"
        v-tooltip.top="{ value: $t('AddColumnDialog.auto-run-approved-tooltip') }">
        <Checkbox v-model="auto_run_for_approved_items" :binary="true" />
        <button class="ml-2 text-xs text-gray-500"
          @click="auto_run_for_approved_items = !auto_run_for_approved_items">
          {{ $t('AddColumnDialog.auto-run-for-approved-items') }}
        </button>
      </div>
      <div class="flex flex-row items-center"
        v-tooltip.top="{ value: $t('AddColumnDialog.auto-run-candidates-tooltip') }">
        <Checkbox v-model="auto_run_for_candidates" :binary="true" />
        <button class="ml-2 text-xs text-gray-500"
          @click="auto_run_for_candidates = !auto_run_for_candidates">
          {{ $t('AddColumnDialog.auto-run-for-candidates') }}
        </button>
      </div>
    </div>

    <div class="flex flex-row items-center" v-if="!use_auto_title">
      <input ref="new_question_name" type="text" v-model="title"
        class="flex-none w-2/3 rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
        :placeholder="$t('AddColumnDialog.column-title-placeholder')" />
    </div>

    <div class="flex flex-row items-center" v-if="!use_auto_prompt">
      <textarea type="text" v-model="custom_prompt"
        class="flex-auto rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
        :placeholder="prompt_label" />
    </div>
    <div class="flex flex-row items-center mb-1" v-if="!use_auto_prompt">
      <div class="text-xs text-gray-500" v-if="selected_module === 'llm'">
        <span v-pre>
          You can use the following placeholders in the prompt:
          <code> {{ title }} </code> for the column title,
          <code> {{ expression }} </code> for the question / task,
          <code> {{ document }} </code> for the input data.<br><br>
          Attention: If <code> {{ document }} </code> is not used, it does not know about the item at all and won't produce meaningful results.
          If <code> {{ expression }} </code> is not used, the question / task is ignored.
        </span>
      </div>
      <div class="text-xs text-gray-500" v-if="selected_module === 'email'">
        <span v-pre>
          You can use the following placeholders in the template:
          <code> {{ document }} </code> for the input data.
        </span>
      </div>
    </div>

    <div class="flex flex-row gap-2 items-center" v-if="!use_default_sources">
      <span class="w-20 text-gray-500">{{ sources_label }}</span>
      <div class="flex-1 min-w-0">
        <MultiSelect v-model="selected_source_fields" :options="collectionStore.available_source_fields" optionLabel="name"
          optionValue="identifier" placeholder="Select Sources..." :maxSelectedLabels="3"
          selectedItemsLabel="{0} Source(s)"
          class="w-full h-full mr-4 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500" />
      </div>
    </div>
    <Message v-if="show_full_text_issue_hint" class="text-gray-500 whitespace-pre-wrap">
      {{ $t('AddColumnDialog.using-full-text-hint-1') }}
      <br>
      {{ $t('AddColumnDialog.using-full-text-hint-2') }}
    </Message>


    <div class="flex flex-row gap-2 flex-wrap" v-if="['llm', 'relevance'].includes(selected_module)">
      <BorderButton v-for="model in default_models" class="flex-1 py-1"
        @click="selected_llm = model.model; use_custom_llm = false"
        :highlighted="selected_llm === model.model">
        <div class="flex flex-col">
          <div class="font-semibold">{{ model.title }}</div>
          <div class="text-xs text-gray-500">{{ model.subtitle }}</div>
        </div>
      </BorderButton>
      <BorderButton class="w-24"
        @click="use_custom_llm = true"
        :highlighted="use_custom_llm">
        <div class="flex flex-col">
          <div class="font-semibold">{{ $t('AddColumnDialog.custom-llm') }}</div>
        </div>
      </BorderButton>
    </div>

    <div v-if="['llm', 'relevance'].includes(selected_module) && use_custom_llm"
      class="flex flex-row gap-2 items-center">
      <LlmSelect class="flex-1 min-w-0" v-model="selected_llm" tooltip="Select the AI model to use">
      </LlmSelect>
    </div>

    <div class="flex flex-row gap-3 mt-4">
      <button v-if="show_process_now_button"
        class="rounded-md border-0 px-2 py-1.5 bg-green-100 font-semibold text-gray-600 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
        type="button"
        @click="add_extraction_question(true)">
        {{ $t('AddColumnDialog.add-and-process-current-page') }}
      </button>
      <button v-if="show_add_without_processing_button"
        class="rounded-md border-0 px-2 py-1.5 font-semibold text-gray-600 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
        type="button"
        @click="add_extraction_question(false)">
        {{ show_process_now_button ? $t('AddColumnDialog.add-without-processing') : $t('AddColumnDialog.add-column') }}
      </button>
    </div>
  </div>
</template>

<style scoped></style>
