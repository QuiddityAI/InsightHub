<script setup>
import { useToast } from 'primevue/usetoast';
import MultiSelect from 'primevue/multiselect';
import Message from 'primevue/message';
import Checkbox from 'primevue/checkbox';

import LanguageSelect from "../widgets/LanguageSelect.vue"
import BorderButton from "../widgets/BorderButton.vue"
import LlmSelect from '../widgets/LlmSelect.vue';

import { httpClient, djangoClient } from "../../api/httpClient"
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { useCollectionStore } from "../../stores/collection_store"
import { FieldType } from "../../utils/utils"

const appState = useAppStateStore()
const mapState = useMapStateStore()
const collectionStore = useCollectionStore()
const toast = useToast()
</script>

<script>
export default {
  inject: ["eventBus"],
  props: ["collection", "collection_class"],
  emits: ["close"],
  data() {
    return {
      selected_source_fields: ['_descriptive_text_fields', '_full_text_snippets'],
      selected_module: 'llm',
      selected_llm: 'Google_Gemini_Flash_1_5_v1',
      default_models: [
        {'title': this.$t('AddColumnDialog.small-ai'), 'subtitle': this.$t('AddColumnDialog.small-ai-subtitle'), 'model': 'Mistral_Ministral8b'},
        {'title': this.$t('AddColumnDialog.medium-ai'), 'subtitle': this.$t('AddColumnDialog.medium-ai-subtitle'), 'model': 'Google_Gemini_Flash_1_5_v1'},
        {'title': this.$t('AddColumnDialog.large-ai'), 'subtitle': this.$t('AddColumnDialog.large-ai-subtitle'), 'model': 'Mistral_Mistral_Large'},
      ],
      selected_language: null,
      show_advanced_modules: false,
      use_auto_title: true,
      use_auto_prompt: true,
      use_auto_language: true,
      use_custom_llm: false,
      use_default_sources: true,
      auto_run_for_approved_items: false,
      auto_run_for_candidates: false,
      title: '',
      expression: '',
      custom_prompt: '',
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
    available_modules() {
      return this.appStateStore.column_modules
    },
    show_full_text_issue_hint() {
      return this.selected_source_fields.find((field) => field !== "_full_text_snippets" && field.includes("full_text"))
    },
    expression_label() {
      if (this.selected_module === 'llm') {
        return this.$t('AddColumnDialog.expression-label-llm')
      } else if (this.selected_module === 'relevance') {
        return this.$t('AddColumnDialog.expression-label-relevance')
      } else if (this.selected_module === 'email') {
        return this.$t('AddColumnDialog.expression-label-email')
      } else {
        return this.$t('AddColumnDialog.expression-label-other')
      }
    },
    sources_label() {
      if (this.selected_module === 'llm' || this.selected_module === 'relevance') {
        return this.$t('AddColumnDialog.sources-label-llm')
      } else if (this.selected_module === 'website_scraping') {
        return this.$t('AddColumnDialog.sources-label-url')
      } else if (this.selected_module === 'web_search') {
        return this.$t('AddColumnDialog.sources-label-web-search')
      } else if (this.selected_module === 'item_field') {
        return this.$t('AddColumnDialog.sources-label-item-field')
      } else {
        return this.$t('AddColumnDialog.sources-label-other')
      }
    },
    prompt_label() {
      if (this.selected_module === 'llm') {
        return this.$t('AddColumnDialog.prompt-label-llm')
      } else if (this.selected_module === 'email') {
        return this.$t('AddColumnDialog.prompt-label-email')
      } else {
        return this.$t('AddColumnDialog.prompt-label-other')
      }
    },
    show_process_now_button() {
      return !['email', 'notes'].includes(this.selected_module)
    },
    show_add_without_processing_button() {
      return !['item_field'].includes(this.selected_module)
    },
  },
  mounted() {
  },
  watch: {
    use_auto_title(value) {
      if (value) {
        this.title = ''
      }
    },
    use_auto_language(value) {
      if (value) {
        this.selected_language = null
      }
    },
    use_auto_prompt(value) {
      if (value) {
        this.custom_prompt = ''
      }
    },
    selected_module(value) {
      this.set_default_values()
    },
  },
  methods: {
    set_default_values() {
      this.use_auto_title = true
      this.use_auto_prompt = true
      this.use_auto_language = true
      this.auto_run_for_approved_items = false
      this.auto_run_for_candidates = false
      this.use_default_sources = true
      if (this.selected_module === 'llm') {
      } else if (this.selected_module === 'relevance') {
        this.auto_run_for_candidates = true
      } else if (this.selected_module === 'website_scraping') {
        this.use_default_sources = false  // always using custom sources
      } else if (this.selected_module === 'web_search') {
        this.use_default_sources = false  // always using custom sources
      } else if (this.selected_module === 'item_field') {
        this.use_default_sources = false  // always using custom sources
        this.auto_run_for_candidates = true
        this.auto_run_for_approved_items = true
        this.use_auto_title = true  // always using field as title
      } else if (this.selected_module === 'email') {
        this.use_auto_language = false  // language must be set
        this.selected_language = 'en'
      } else if (this.selected_module === 'notes') {
        this.auto_run_for_candidates = false
        this.auto_run_for_approved_items = false
      }
      if (['item_field', 'web_search', 'website_scraping'].includes(this.selected_module)) {
        this.selected_source_fields = []
      } else {
        this.selected_source_fields = ['_descriptive_text_fields', '_full_text_snippets']
      }
    },
    add_extraction_question(process_current_page=false) {
      // TODO: check for missing values
      const parameters = {}
      if (['llm', 'relevance', 'email'].includes(this.selected_module)) {
        parameters.model = this.selected_llm
      }
      if (['llm', 'relevance', 'email'].includes(this.selected_module)) {
        parameters.language = this.selected_language
      }
      let field_type = FieldType.TEXT
      if (['relevance'].includes(this.selected_module)) {
        field_type = FieldType.ARBITRARY_OBJECT
      }
      const body = {
        collection_id: this.collectionStore.collection_id,
        field_type: field_type,
        name: this.title,
        expression: this.expression,
        source_fields: this.selected_source_fields,
        module: this.selected_module,
        prompt_template: this.custom_prompt,
        auto_run_for_approved_items: this.auto_run_for_approved_items,
        auto_run_for_candidates: this.auto_run_for_candidates,
        parameters: parameters,
      }
      httpClient.post(`/api/v1/columns/add_column`, body)
      .then((response) => {
        if (!this.collection.columns) {
          this.collection.columns = []
        }
        const column = response.data
        this.collection.columns.push(column)
        if (process_current_page) {
          this.collectionStore.extract_question(column.id, true)
        }
      })
      .catch((error) => {
        console.error(error)
      })
      this.$emit('close')
    },
  },
}
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
