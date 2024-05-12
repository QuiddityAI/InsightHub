<script setup>
import {
  TrashIcon,
} from "@heroicons/vue/24/outline"
import { useToast } from 'primevue/usetoast';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Button from 'primevue/button';
import MultiSelect from 'primevue/multiselect';
import Paginator from "primevue/paginator"
import OverlayPanel from 'primevue/overlaypanel';
import Dropdown from 'primevue/dropdown';

import CollectionItem from "./CollectionItem.vue"
import ExportTableArea from "./ExportTableArea.vue";
import { FieldType } from "../../utils/utils"
import { httpClient, djangoClient } from "../../api/httpClient"
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
const appState = useAppStateStore()
const mapState = useMapStateStore()
const toast = useToast()
</script>

<script>

export default {
  inject: ["eventBus"],
  props: ["collection_id", "class_name", "initial_collection"],
  emits: [],
  data() {
    return {
      collection_items: [],
      collection: this.initial_collection,
      is_processing: false,
      selected_source_fields: ['_descriptive_text_fields', '_full_text_snippets'],
      selected_module: 'groq_llama_3_70b',
      available_modules: [
        { identifier: 'openai_gpt_3_5', name: 'GPT 3.5 (medium accuracy and cost)' },
        { identifier: 'openai_gpt_4_turbo', name: 'GPT 4 Turbo (highest accuracy and cost, slow)' },
        { identifier: 'groq_llama_3_8b', name: 'Llama 3 (B (lowest cost, low accuracy, super fast)' },
        { identifier: 'groq_llama_3_70b', name: 'Llama 3 70B (low cost, medium accuracy, fast)' },
        { identifier: 'python_expression', name: 'Python Expression' },
        { identifier: 'website_scraping', name: 'Website Text Extraction' },
      ],
      first_index: 0,
      per_page: 10,
      selected_extraction_question: null,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    available_source_fields() {
      const dataset_ids = new Set()
      for (const item of this.collection_items) {
        const dataset_id = item.dataset_id
        dataset_ids.add(dataset_id)
      }
      const available_fields = {}
      for (const dataset_id of dataset_ids) {
        const dataset = this.appStateStore.datasets[dataset_id]
        for (const field of Object.values(dataset.object_fields)) {
          available_fields[field.identifier] = {
            identifier: field.identifier,
            name: field.description || field.identifier,
          }
        }
      }
      available_fields['_descriptive_text_fields'] = {
        identifier: '_descriptive_text_fields',
        name: 'Descriptive Text',
      }
      available_fields['_full_text_snippets'] = {
        identifier: '_full_text_snippets',
        name: 'Full Text Excerpts',
      }
      return Object.values(available_fields).sort((a, b) => a.identifier.localeCompare(b.identifier))
    },
    item_count() {
      const class_details = this.collection.actual_classes.find((actual_class) => actual_class.name === this.class_name)
      return class_details["positive_count"]
    }
  },
  mounted() {
    this.load_collection_items()
  },
  watch: {
    first_index() {
      this.load_collection_items()
    },
  },
  methods: {
    load_collection_items() {
      const that = this
      const body = {
        collection_id: this.collection.id,
        class_name: this.class_name,
        type: FieldType.IDENTIFIER,
        is_positive: true,
        offset: this.first_index,
        limit: this.per_page,
      }
      httpClient.post("/org/data_map/get_collection_items", body).then(function (response) {
        that.collection_items = response.data
      })
    },
    load_collection(on_success=null) {
      const that = this
      const body = {
        collection_id: this.collection.id,
      }
      httpClient.post("/org/data_map/get_collection", body).then(function (response) {
        that.collection = response.data
        if (on_success) {
          on_success()
        }
      })
    },
    add_extraction_question(name, prompt) {
      if (!name || !prompt || !this.selected_source_fields.length) {
        return
      }
      const that = this
      const body = {
        collection_id: this.collection_id,
        name: name,
        prompt: prompt,
        source_fields: this.selected_source_fields,
        module: this.selected_module,
      }
      httpClient.post(`/org/data_map/add_collection_extraction_question`, body)
      .then(function (response) {
        if (!that.collection.extraction_questions) {
          that.collection.extraction_questions = []
        }
        that.collection.extraction_questions.push({name, prompt, source_fields: that.selected_source_fields})
      })
      .catch(function (error) {
        console.error(error)
      })
      this.$refs.new_question_name.value = ''
      this.$refs.new_question_prompt.value = ''
    },
    delete_extraction_question(question) {
      const that = this
      if (!confirm("Are you sure you want to delete this question and all of the extraction results and notes?")) {
        return
      }
      this.remove_results(question, false, true, () => {
        const body = {
          collection_id: this.collection_id,
          question_name: question.name,
        }
        httpClient.post(`/org/data_map/delete_collection_extraction_question`, body)
        .then(function (response) {
          that.collection.extraction_questions = that.collection.extraction_questions.filter((other_question) => other_question.name !== question.name)
        })
        .catch(function (error) {
          console.error(error)
        })
      })
    },
    remove_results(question, only_current_page=true, force=false, on_success=null) {
      const that = this
      if (!only_current_page && !force && !confirm("This will remove the extraction results for all items in the collection. Are you sure?")) {
        return
      }
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
        question_name: question.name,
        offset: only_current_page ? this.first_index : 0,
        limit: only_current_page ? this.per_page : -1,
      }
      httpClient.post(`/org/data_map/remove_collection_class_extraction_results`, body)
      .then(function (response) {
        if (on_success) {
          on_success()
        }
        that.get_extraction_results(question.name)
      })
      .catch(function (error) {
        console.error(error)
      })
    },
    extract_question(question, only_current_page=true) {
      const that = this
      if (!only_current_page && !confirm("This will extract the question for all items in the collection. This might be long running and expensive. Are you sure?")) {
        return
      }
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
        question_name: question.name,
        offset: only_current_page ? this.first_index : 0,
        limit: only_current_page ? this.per_page : -1,
      }
      httpClient.post(`/org/data_map/extract_question_from_collection_class_items`, body)
      .then(function (response) {
        that.is_processing = true
        that.collection = response.data
        that.get_extraction_results(question.name)
      })
      .catch(function (error) {
        console.error(error)
      })
    },
    get_extraction_results(question_name) {
      this.load_collection_items()
      this.load_collection(() => {
        if (this.collection.current_extraction_processes.includes(question_name)) {
          setTimeout(() => {
            this.get_extraction_results(question_name)
          }, 1000)
        } else {
          this.is_processing = false
        }
      })
    },
    human_readable_source_fields(fields) {
      return fields.map((field) => this.available_source_fields.find((f) => f.identifier === field).name).join(", ")
    },
  },
}
</script>

<template>
  <div>

    <div class="w-full flex flex-row mb-3">
      <div class="flex-initial w-2/3 flex flex-row">
        <input
          ref="new_question_name"
          type="text"
          class="flex-none w-40 rounded-l-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
          placeholder="Column Name"/>
        <input
          ref="new_question_prompt"
          type="text"
          class="flex-auto rounded-l-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
          placeholder="Question / Prompt"
          @keyup.enter="add_extraction_question($refs.new_question_name.value, $refs.new_question_prompt.value)"/>
        <div class="flex-initial w-40">
          <MultiSelect v-model="selected_source_fields"
            :options="available_source_fields"
            optionLabel="name"
            optionValue="identifier"
            placeholder="Select Sources..."
            :maxSelectedLabels="0"
            selectedItemsLabel="{0} Source(s)"
            class="w-full h-full mr-4 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500" />
        </div>
        <div class="flex-initial w-36">
          <Dropdown v-model="selected_module"
            :options="available_modules"
            optionLabel="name"
            optionValue="identifier"
            placeholder="Select Module.."
            class="w-full h-full mr-4 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500" />
        </div>
        <button
          class="rounded-r-md border-0 px-2 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
          type="button"
          @click="add_extraction_question($refs.new_question_name.value, $refs.new_question_prompt.value)">
          Add Question
        </button>
      </div>
      <div class="flex-1"></div>
      <button @click="event => {$refs.export_dialog.toggle(event)}"
        class="py-1 px-2 rounded-md bg-gray-100 hover:bg-blue-100/50">
        Export
      </button>

      <OverlayPanel ref="export_dialog">
        <ExportTableArea :collection_id="collection_id" :class_name="class_name">
        </ExportTableArea>
      </OverlayPanel>
    </div>

    <div v-if="is_processing">
      Processing...
    </div>

    <Paginator v-model:first="first_index" :rows="per_page" :total-records="item_count"
      class="mt-[0px]"></Paginator>

    <DataTable :value="collection_items" tableStyle="">
        <Column header="Item">
          <template #body="slotProps">
            <CollectionItem
              :dataset_id="slotProps.data.dataset_id"
              :item_id="slotProps.data.item_id"
              :is_positive="slotProps.data.is_positive"
              @remove="remove_collection_item(slotProps.data.id)"
              class="w-[520px]">
            </CollectionItem>
          </template>
        </Column>
        <Column v-for="question in collection.extraction_questions" :header="false">
          <template #header="slotProps">
            <button class="rounded-md bg-gray-100 hover:bg-blue-100/50 py-1 px-2"
              @click="event => {selected_extraction_question = question; $refs.column_options.toggle(event)}">
              {{ question.name }}
            </button>
          </template>
          <template #body="slotProps">
            {{ slotProps.data.extraction_answers[question.name] || "" }}
          </template>
        </Column>
    </DataTable>

    <OverlayPanel ref="column_options">
        <div class="w-[400px] flex flex-col gap-2">
          <!-- <h3 class="font-bold">{{ selected_extraction_question.name }}</h3> -->
          <div class="flex flex-row">
            <p class="flex-1">{{ selected_extraction_question.prompt }}</p>
            <button
              @click="delete_extraction_question(selected_extraction_question); $refs.column_options.hide()"
              class="flex h-6 w-6 items-center justify-center rounded text-gray-400 hover:bg-gray-100 hover:text-red-500">
              <TrashIcon class="h-4 w-4"></TrashIcon>
            </button>
          </div>
          <p class="text-xs text-gray-500">{{ human_readable_source_fields(selected_extraction_question.source_fields) }}</p>
          <p class="text-xs text-gray-500">{{ available_modules.find((m) => m.identifier === selected_extraction_question.module)?.name }}</p>
          <div class="flex flex-row gap-2">
            <button @click="extract_question(selected_extraction_question, true)"
              class="flex-1 p-1 bg-gray-100 hover:bg-blue-100/50 rounded text-sm">
              Extract <span class="text-gray-500">(current page)</span></button>
            <button @click="extract_question(selected_extraction_question, false)"
              class="flex-1 p-1 bg-gray-100 hover:bg-blue-100/50 rounded text-sm">
              Extract <span class="text-gray-500">(all)</span></button>
          </div>

          <div class="flex flex-row gap-2">
            <button @click="remove_results(selected_extraction_question, true)"
              class="flex-1 p-1 bg-gray-100 hover:bg-blue-100/50 rounded text-sm">
              Remove results<br><span class="text-gray-500">(current page)</span></button>
            <button @click="remove_results(selected_extraction_question, false)"
              class="flex-1 p-1 bg-gray-100 hover:bg-blue-100/50 rounded text-sm">
              Remove results<br><span class="text-gray-500">(all)</span></button>
          </div>
        </div>
    </OverlayPanel>

    <Paginator v-model:first="first_index" :rows="per_page" :total-records="item_count"
      class="mt-[0px]"></Paginator>

  </div>

</template>

<style scoped>
</style>
