<script setup>
import { useToast } from 'primevue/usetoast';
import Dropdown from 'primevue/dropdown';
import MultiSelect from 'primevue/multiselect';
import Message from 'primevue/message';

import { httpClient, djangoClient } from "../../api/httpClient"
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { FieldType } from "../../utils/utils"

const appState = useAppStateStore()
const mapState = useMapStateStore()
const toast = useToast()
</script>

<script>

export default {
  inject: ["eventBus"],
  props: ["collection", "collection_class", "collection_items"],
  emits: ["close"],
  data() {
    return {
      selected_source_fields: ['_descriptive_text_fields', '_full_text_snippets'],
      selected_module: 'openai_gpt_4_o',
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    included_datasets() {
      const dataset_ids = new Set()
      for (const item of this.collection_items) {
        const dataset_id = item.dataset_id
        dataset_ids.add(dataset_id)
      }
      return Array.from(dataset_ids).map((dataset_id) => this.appStateStore.datasets[dataset_id])
    },
    available_source_fields() {
      const available_fields = {}
      const unsupported_field_types = [FieldType.VECTOR, FieldType.CLASS_PROBABILITY, FieldType.ARBITRARY_OBJECT]
      function capitalizeFirstLetter(string) {
        return string.charAt(0).toUpperCase() + string.slice(1);
      }
      for (const dataset of this.included_datasets) {
        if (!dataset?.schema?.object_fields) continue
        for (const field of Object.values(dataset.schema.object_fields)) {
          if (unsupported_field_types.includes(field.field_type)) {
            continue
          }
          available_fields[field.identifier] = {
            identifier: field.identifier,
            name: `${capitalizeFirstLetter(dataset.schema.entity_name)}: ${field.name || field.identifier}`,
          }
        }
      }
      for (const column of this.collection.columns) {
        available_fields[column.identifier] = {
          identifier: '_column__' + column.identifier,
          name: `Column: ${column.name}`,
        }
      }
      available_fields['_descriptive_text_fields'] = {
        identifier: '_descriptive_text_fields',
        name: 'All short descriptive text fields',
      }
      available_fields['_full_text_snippets'] = {
        identifier: '_full_text_snippets',
        name: 'Full text excerpts',
      }
      return Object.values(available_fields).sort((a, b) => a.identifier.localeCompare(b.identifier))
    },
    available_modules() {
      return this.appStateStore.available_ai_modules.concat(this.appStateStore.additional_column_modules)
    },
    show_full_text_issue_hint() {
      return this.selected_source_fields.find((field) => field !== "_full_text_snippets" && field.includes("full_text"))
    },
  },
  mounted() {
  },
  watch: {
  },
  methods: {

  },
}
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="flex flex-row items-center">
      <input ref="new_question_name" type="text"
        class="flex-none w-2/3 rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
        placeholder="Column Name" />
    </div>
    <div class="flex flex-row gap-2 items-center">
      <div class="flex-1 min-w-0">
        <MultiSelect v-model="selected_source_fields" :options="available_source_fields" optionLabel="name"
          optionValue="identifier" placeholder="Select Sources..." :maxSelectedLabels="0"
          selectedItemsLabel="{0} Source(s)"
          class="w-full h-full mr-4 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500" />
      </div>
      <div class="flex-1 min-w-0">
        <Dropdown v-model="selected_module" :options="available_modules" optionLabel="name" optionValue="identifier"
          placeholder="Select Module.."
          class="w-full h-full mr-4 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500" />
      </div>
    </div>
    <Message v-if="show_full_text_issue_hint" class="text-gray-500">
      Using the full text of an item might be slow and expensive. The full text will also be limited to the
      maximum text length of the AI module, which might lead to unpredictable results.
      <br>
      Consider using 'Full Text Excerpts' instead, which selects only the most relevant parts of the full text.
    </Message>
    <div class="flex flex-row items-center">
      <textarea ref="new_question_prompt" type="text"
        class="flex-auto rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
        placeholder="Question / Prompt" />
    </div>
    <div class="flex flex-row gap-3">
      <button
        class="rounded-md border-0 px-2 py-1.5 bg-green-100 font-semibold text-gray-600 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
        type="button"
        @click="show_add_column_dialog = false; add_extraction_question($refs.new_question_name.value, $refs.new_question_prompt.value, true)">
        Add Question & Process Current Page
      </button>
      <button
        class="rounded-md border-0 px-2 py-1.5 font-semibold text-gray-600 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
        type="button"
        @click="show_add_column_dialog = false; add_extraction_question($refs.new_question_name.value, $refs.new_question_prompt.value, false)">
        Add without Processing
      </button>
    </div>
  </div>
</template>

<style scoped></style>
