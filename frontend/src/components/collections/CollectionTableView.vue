<script setup>
import { useToast } from 'primevue/usetoast';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Button from 'primevue/button';
import MultiSelect from 'primevue/multiselect';

import CollectionItem from "./CollectionItem.vue"
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
      items: [],
      collection: this.initial_collection,
      is_processing: false,
      selected_source_fields: ['_descriptive_text_fields'],
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    available_source_fields() {
      const dataset_ids = new Set()
      for (const item of this.items) {
        const [dataset_id, item_id] = JSON.parse(item.value)
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
        name: 'Descriptive Text Fields',
      }
      available_fields['_full_text_chunk_embeddings'] = {
        identifier: '_full_text_chunk_embeddings',
        name: 'Full Text Excerpts',
      }
      return Object.values(available_fields)
    }
  },
  mounted() {
    this.load_items()
  },
  watch: {
  },
  methods: {
    load_items(is_positive=true) {
      const that = this
      const body = {
        collection_id: this.collection.id,
        class_name: this.class_name,
        type: FieldType.IDENTIFIER,
        is_positive: is_positive,
      }
      httpClient.post("/org/data_map/get_collection_items", body).then(function (response) {
        that.items = response.data
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
    remove_results(question) {
      const that = this
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
        question_name: question.name,
      }
      httpClient.post(`/org/data_map/remove_collection_class_extraction_results`, body)
      .then(function (response) {
        that.get_extraction_results(question.name)
      })
      .catch(function (error) {
        console.error(error)
      })
    },
    extract_question(question) {
      const that = this
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
        question_name: question.name,
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
      this.load_items()
      this.load_collection(() => {
        if (this.collection.current_extraction_processes.includes(question_name)) {
          setTimeout(() => {
            this.get_extraction_results(question_name)
          }, 1000)
        } else {
          this.is_processing = false
        }
      })
    }
  },
}
</script>

<template>
  <div>
    <div class="w-2/3">
      <div class="flex flex-col">
        <div v-for="question in collection.extraction_questions" class="">
          • {{  question.name }}: {{ question.prompt }} ({{ question.source_fields.join(", ") }})
          <button @click="extract_question(question)" class="p-1 mr-2 bg-gray-100 hover:bg-blue-100/50 rounded">Extract now</button>
          <button @click="remove_results(question)" class="p-1 bg-gray-100 hover:bg-blue-100/50 rounded">Remove results</button>
        </div>
      </div>

      <div class="my-2 flex items-stretch">
        <input
          ref="new_question_name"
          type="text"
          class="flex-none w-40 rounded-l-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
          placeholder="Question Name"/>
        <input
          ref="new_question_prompt"
          type="text"
          class="flex-auto rounded-l-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
          placeholder="Prompt"
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
        <button
          class="rounded-r-md border-0 px-2 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
          type="button"
          @click="add_extraction_question($refs.new_question_name.value, $refs.new_question_prompt.value)">
          Add Question
        </button>
      </div>
    </div>

    <div v-if="is_processing">
      Processing...
    </div>

    <DataTable :value="items" tableStyle="">
        <Column header="Item">
          <template #body="slotProps">
            <CollectionItem
              :dataset_id="JSON.parse(slotProps.data.value)[0]"
              :item_id="JSON.parse(slotProps.data.value)[1]"
              :is_positive="slotProps.data.is_positive"
              @remove="remove_collection_item(slotProps.data.id)"
              class="w-[600px]">
            </CollectionItem>
          </template>
        </Column>
        <Column v-for="question in collection.extraction_questions" :header="question.name">
          <template #body="slotProps">
            {{ slotProps.data.extraction_answers[question.name] || "" }}
          </template>
        </Column>

    </DataTable>

  </div>

</template>

<style scoped>
</style>
