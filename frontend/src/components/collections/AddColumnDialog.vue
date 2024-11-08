<script setup>
import { useToast } from 'primevue/usetoast';
import Dropdown from 'primevue/dropdown';
import MultiSelect from 'primevue/multiselect';
import Message from 'primevue/message';
import Checkbox from 'primevue/checkbox';

import LanguageSelect from "../widgets/LanguageSelect.vue"
import BorderButton from "../widgets/BorderButton.vue"

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
        {'title': 'Small AI', 'subtitle': 'cheap + fast, simple', 'model': 'Mistral_Ministral8b'},
        {'title': 'Medium AI', 'subtitle': 'balanced', 'model': 'Google_Gemini_Flash_1_5_v1'},
        {'title': 'Large AI', 'subtitle': 'expensive + slow, smart', 'model': 'Mistral_Mistral_Large'},
      ],
      available_llm_models: [],
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
        return 'Query / Task'
      } else if (this.selected_module === 'relevance') {
        return 'Relevance Criteria'
      } else if (this.selected_module === 'email') {
        return 'E-Mail addresses (comma-separated)'
      } else {
        return 'Expression'
      }
    },
    sources_label() {
      if (this.selected_module === 'llm' || this.selected_module === 'relevance') {
        return 'Sources:'
      } else if (this.selected_module === 'website_scraping') {
        return 'URL Field:'
      } else if (this.selected_module === 'web_search') {
        return 'Query:'
      } else if (this.selected_module === 'item_field') {
        return 'Field:'
      } else {
        return 'Sources:'
      }
    },
    prompt_label() {
      if (this.selected_module === 'llm') {
        return 'Custom Prompt (see explanation below)'
      } else if (this.selected_module === 'email') {
        return 'E-Mail Template (see explanation below)'
      } else {
        return 'Prompt'
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
    this.get_available_llm_models()
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
    get_available_llm_models() {
      httpClient.get(`/api/v1/columns/available_llm_models`)
      .then((response) => {
        this.available_llm_models = response.data
      })
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
        {{ module.name }}
      </BorderButton>
      <BorderButton v-tooltip.top="{ value: 'Show advanced modules' }"
        @click="show_advanced_modules = !show_advanced_modules"
        :highlighted="show_advanced_modules">
        ...
      </BorderButton>
    </div>
    <div class="flex flex-row items-center gap-2 flex-wrap" v-if="show_advanced_modules">
      <BorderButton v-for="module in appState.column_modules.filter(module => !module.highlight)"
        @click="selected_module = module.identifier"
        :highlighted="selected_module === module.identifier">
        {{ module.name }}
      </BorderButton>
    </div>
    <div class="text-xs text-gray-500">
      {{ appState.column_modules.find(module => module.identifier === selected_module).help_text }}
    </div>

    <div class="flex flex-row items-center mb-4 mt-4" v-if="['llm', 'relevance', 'email'].includes(selected_module)">
      <textarea type="text" v-model="expression"
        class="flex-auto rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
        :placeholder="expression_label" />
      <LanguageSelect v-if="!use_auto_language"
        :available_language_codes="['en', 'de']"
        v-model="selected_language"
        :offer_wildcard="true" :use_last_used_language="false"
        tooltip="Language of the question and results ('world' for auto-detect)">
      </LanguageSelect>
    </div>

    <div class="flex flex-row gap-5 items-center">
      <div class="flex flex-row items-center"
        v-tooltip.top="{ value: 'Auto-set title of column' }">
        <Checkbox v-model="use_auto_title" :binary="true" />
        <button class="ml-2 text-xs text-gray-500"
          @click="use_auto_title = !use_auto_title">
          Auto Title
        </button>
      </div>
      <div class="flex flex-row items-center" v-if="['llm', 'relevance'].includes(selected_module)"
        v-tooltip.top="{ value: 'Auto-set title of column' }">
        <Checkbox v-model="use_auto_language" :binary="true" />
        <button class="ml-2 text-xs text-gray-500"
          @click="use_auto_language = !use_auto_language">
          Auto Language
        </button>
      </div>
      <div class="flex flex-row items-center" v-if="['llm', 'email'].includes(selected_module)"
        v-tooltip.top="{ value: 'Uncheck to use a custom prompt' }">
        <Checkbox v-model="use_auto_prompt" :binary="true" />
        <button class="ml-2 text-xs text-gray-500"
          @click="use_auto_prompt = !use_auto_prompt">
          {{ selected_module == 'email' ? 'Default Template' : 'Auto Prompt' }}
        </button>
      </div>
      <div class="flex flex-row items-center" v-if="['llm', 'relevance', 'email'].includes(selected_module)"
        v-tooltip.top="{ value: 'Uncheck if anything beside the items text fields is relevant' }">
        <Checkbox v-model="use_default_sources" :binary="true" />
        <button class="ml-2 text-xs text-gray-500"
          @click="use_default_sources = !use_default_sources">
          Default Sources
        </button>
      </div>
    </div>

    <div class="flex flex-row gap-5 items-center" v-if="!['notes', 'item_field'].includes(selected_module)">
      <div class="flex flex-row items-center"
        v-tooltip.top="{ value: 'Execute this as soon as an item is approved' }">
        <Checkbox v-model="auto_run_for_approved_items" :binary="true" />
        <button class="ml-2 text-xs text-gray-500"
          @click="auto_run_for_approved_items = !auto_run_for_approved_items">
          Auto-run for Approved Items
        </button>
      </div>
      <div class="flex flex-row items-center"
        v-tooltip.top="{ value: 'Execute this automatically for candidates (e.g. search results)' }">
        <Checkbox v-model="auto_run_for_candidates" :binary="true" />
        <button class="ml-2 text-xs text-gray-500"
          @click="auto_run_for_candidates = !auto_run_for_candidates">
          Auto-run for Candidates
        </button>
      </div>
    </div>

    <div class="flex flex-row items-center" v-if="!use_auto_title">
      <input ref="new_question_name" type="text" v-model="title"
        class="flex-none w-2/3 rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
        placeholder="Column Title" />
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
    <Message v-if="show_full_text_issue_hint" class="text-gray-500">
      Using the full text of an item might be slow and expensive. The full text will also be limited to the
      maximum text length of the AI module, which might lead to unpredictable results.
      <br>
      Consider using 'Full Text Excerpts' instead, which selects only the most relevant parts of the full text.
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
          <div class="font-semibold">Custom</div>
        </div>
      </BorderButton>
    </div>

    <div v-if="['llm', 'relevance'].includes(selected_module) && use_custom_llm"
      class="flex flex-row gap-2 items-center">
      <div class="flex-1 min-w-0">
        <Dropdown v-model="selected_llm" :options="available_llm_models" optionLabel="verbose_name" optionValue="model_id"
          placeholder="Select LLM..."
          class="w-full h-full mr-4 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500" />
      </div>
    </div>

    <div class="flex flex-row gap-3 mt-4">
      <button v-if="show_process_now_button"
        class="rounded-md border-0 px-2 py-1.5 bg-green-100 font-semibold text-gray-600 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
        type="button"
        @click="add_extraction_question(true)">
        Add & Process Current Page
      </button>
      <button v-if="show_add_without_processing_button"
        class="rounded-md border-0 px-2 py-1.5 font-semibold text-gray-600 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
        type="button"
        @click="add_extraction_question(false)">
        {{ show_process_now_button ? 'Add without Processing' : 'Add Column' }}
      </button>
    </div>
  </div>
</template>

<style scoped></style>
