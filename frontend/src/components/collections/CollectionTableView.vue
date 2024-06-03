<script setup>
import {
  TrashIcon,
  PlusIcon,
  ChevronRightIcon,
} from "@heroicons/vue/24/outline"
import { useToast } from 'primevue/usetoast';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Button from 'primevue/button';
import MultiSelect from 'primevue/multiselect';
import Paginator from "primevue/paginator"
import OverlayPanel from 'primevue/overlaypanel';
import Dropdown from 'primevue/dropdown';
import Message from 'primevue/message';
import Dialog from "primevue/dialog";
import Textarea from 'primevue/textarea';

import WritingTaskArea from "./WritingTaskArea.vue";
import CollectionItem from "./CollectionItem.vue"
import ExportTableArea from "./ExportTableArea.vue";
import CollectionTableCell from "./CollectionTableCell.vue";
import ObjectDetailsModal from "../search/ObjectDetailsModal.vue";
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
  props: ["collection_id", "class_name"],
  emits: [],
  data() {
    return {
      collection: useAppStateStore().collections.find((collection) => collection.id === this.collection_id),
      collection_items: [],

      show_add_column_dialog: false,
      selected_source_fields: ['_descriptive_text_fields', '_full_text_snippets'],
      selected_module: 'openai_gpt_4_o',

      first_index: 0,
      per_page: 10,
      order_by_field: 'date_added',
      order_descending: true,

      selected_column: null,

      show_details_dialog: false,

      show_writing_tasks: false,
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
      for (const dataset of this.included_datasets) {
        if (!dataset?.schema?.object_fields) continue
        for (const field of Object.values(dataset.schema.object_fields)) {
          available_fields[field.identifier] = {
            identifier: field.identifier,
            name: field.name || field.identifier,
          }
        }
      }
      for (const column of this.collection.columns) {
        available_fields[column.identifier] = {
          identifier: '_column__' + column.identifier,
          name: column.name,
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
    available_order_by_fields() {
      const available_fields = {}
      for (const column of this.collection.columns) {
        available_fields[column.identifier] = {
          identifier: 'column_data__' + column.identifier + '__value',
          name: column.name,
        }
      }
      available_fields['date_added'] = {
        identifier: 'date_added',
        name: 'Date Added',
      }
      available_fields['changed_at'] = {
        identifier: 'changed_at',
        name: 'Last Changed',
      }
      return Object.values(available_fields)
    },
    available_modules() {
      return this.appStateStore.available_ai_modules.concat(this.appStateStore.additional_column_modules)
    },
    show_full_text_issue_hint() {
      return this.selected_source_fields.find((field) => field !== "_full_text_snippets" && field.includes("full_text"))
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
    order_by_field() {
      this.load_collection_items()
    },
    order_descending() {
      this.load_collection_items()
    },
    'appStateStore.selected_document_ds_and_id'() {
      this.show_details_dialog = !!this.appStateStore.selected_document_ds_and_id
    },
  },
  methods: {
    load_collection_items(only_update_specific_columns=null) {
      const that = this
      const body = {
        collection_id: this.collection.id,
        class_name: this.class_name,
        type: FieldType.IDENTIFIER,
        is_positive: true,
        offset: this.first_index,
        limit: this.per_page,
        order_by: (this.order_descending ? "-" : "") + this.order_by_field,
        include_column_data: true,
      }
      httpClient.post("/org/data_map/get_collection_items", body).then(function (response) {
        if (only_update_specific_columns) {
          for (const item of response.data) {
            const existing_item = that.collection_items.find((i) => i.id === item.id)
            if (!existing_item) continue
            for (const column_identifier of only_update_specific_columns) {
              existing_item.column_data[column_identifier] = item.column_data[column_identifier]
            }
          }
        } else {
          that.collection_items = response.data
        }
      })
    },
    update_collection(on_success=null) {
      const that = this
      const body = {
        collection_id: this.collection.id,
      }
      httpClient.post("/org/data_map/get_collection", body).then(function (response) {
        if (JSON.stringify(response.data.columns) !== JSON.stringify(that.collection.columns)) {
          that.collection.columns = response.data.columns
        }
        that.collection.current_extraction_processes = response.data.current_extraction_processes

        if (on_success) {
          on_success()
        }
      })
    },
    add_extraction_question(name, prompt, process_current_page=false) {
      if (!name || !prompt || !this.selected_source_fields.length) {
        return
      }
      const that = this
      const body = {
        collection_id: this.collection_id,
        field_type: FieldType.TEXT,
        name: name,
        expression: prompt,
        source_fields: this.selected_source_fields,
        module: this.selected_module,
      }
      httpClient.post(`/org/data_map/add_collection_column`, body)
      .then(function (response) {
        if (!that.collection.columns) {
          that.collection.columns = []
        }
        const column = response.data
        that.collection.columns.push(column)
        if (process_current_page) {
          that.extract_question(column.id, true)
        }
      })
      .catch(function (error) {
        console.error(error)
      })
      this.$refs.new_question_name.value = ''
      this.$refs.new_question_prompt.value = ''
    },
    delete_column(column_id) {
      const that = this
      if (!confirm("Are you sure you want to delete this column and all of the extraction results and notes?")) {
        return
      }
      const body = {
        column_id: column_id,
      }
      httpClient.post(`/org/data_map/delete_collection_column`, body)
      .then(function (response) {
        that.collection.columns = that.collection.columns.filter((column) => column.id !== column_id)
      })
      .catch(function (error) {
        console.error(error)
      })
    },
    remove_results(column_id, only_current_page=true, force=false, on_success=null) {
      const that = this
      if (!only_current_page && !force && !confirm("This will remove the column content for all items in the collection. Are you sure?")) {
        return
      }
      const body = {
        column_id: column_id,
        class_name: this.class_name,
        offset: only_current_page ? this.first_index : 0,
        limit: only_current_page ? this.per_page : -1,
        order_by: (this.order_descending ? "-" : "") + this.order_by_field,
      }
      httpClient.post(`/org/data_map/remove_collection_class_column_data`, body)
      .then(function (response) {
        if (on_success) {
          on_success()
        }
        that.get_extraction_results(column_id)
      })
      .catch(function (error) {
        console.error(error)
      })
    },
    extract_question(column_id, only_current_page=true) {
      const that = this
      if (!only_current_page && !confirm("This will extract the question for all items in the collection. This might be long running and expensive. Are you sure?")) {
        return
      }
      const body = {
        column_id: column_id,
        class_name: this.class_name,
        offset: only_current_page ? this.first_index : 0,
        limit: only_current_page ? this.per_page : -1,
        order_by: (this.order_descending ? "-" : "") + this.order_by_field,
      }
      httpClient.post(`/org/data_map/extract_question_from_collection_class_items`, body)
      .then(function (response) {
        that.collection.current_extraction_processes = response.data.current_extraction_processes
        that.get_extraction_results(column_id)
      })
      .catch(function (error) {
        console.error(error)
      })
    },
    get_extraction_results(column_id) {
      const column_identifier = this.collection.columns.find((column) => column.id === column_id).identifier
      this.load_collection_items([column_identifier])
      this.update_collection(() => {
        if (this.collection.current_extraction_processes.includes(column_identifier)) {
          setTimeout(() => {
            this.get_extraction_results(column_id)
          }, 1000)
        }
      })
    },
    human_readable_source_fields(fields) {
      return fields.map((field) => this.available_source_fields.find((f) => f.identifier === field).name).join(", ")
    },
    human_readable_module_name(module_identifier) {
      return this.available_modules.find((m) => m.identifier === module_identifier)?.name
    },
  },
}
</script>

<template>
  <div class="h-full w-full flex flex-row">
    <div class="flex-1 flex flex-col overflow-x-hidden">

      <div class="w-full flex flex-row mb-3">
        <button @click="show_add_column_dialog = true" class="py-1 px-2 rounded-md bg-green-100 font-semibold hover:bg-blue-100/50">
          Add Column <PlusIcon class="inline h-4 w-4"></PlusIcon>
        </button>
        <Dialog v-model:visible="show_add_column_dialog" modal header="Add Column">
          <div class="flex flex-col gap-3">
            <div class="flex flex-row items-center">
              <input
                ref="new_question_name"
                type="text"
                class="flex-none w-2/3 rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
                placeholder="Column Name"/>
            </div>
            <div class="flex flex-row gap-2 items-center">
              <div class="flex-1 min-w-0">
                <MultiSelect v-model="selected_source_fields"
                  :options="available_source_fields"
                  optionLabel="name"
                  optionValue="identifier"
                  placeholder="Select Sources..."
                  :maxSelectedLabels="0"
                  selectedItemsLabel="{0} Source(s)"
                  class="w-full h-full mr-4 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500" />
              </div>
              <div class="flex-1 min-w-0">
                <Dropdown v-model="selected_module"
                  :options="available_modules"
                  optionLabel="name"
                  optionValue="identifier"
                  placeholder="Select Module.."
                  class="w-full h-full mr-4 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500" />
              </div>
            </div>
            <Message v-if="show_full_text_issue_hint" class="text-gray-500">
              Using the full text of an item might be slow and expensive. The full text will also be limited to the maximum text length of the AI module, which might lead to unpredictable results.
              <br>
              Consider using 'Full Text Excerpts' instead, which selects only the most relevant parts of the full text.
            </Message>
            <div class="flex flex-row items-center">
              <textarea
                ref="new_question_prompt"
                type="text"
                class="flex-auto rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
                placeholder="Question / Prompt"/>
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
        </Dialog>

        <div class="flex-1"></div>
        <button @click="event => {$refs.export_dialog.toggle(event)}"
          class="py-1 px-2 rounded-md bg-gray-100 hover:bg-blue-100/50">
          Export
        </button>
        <button v-if="appState.user.is_staff" @click="show_writing_tasks = !show_writing_tasks"
          class="ml-2 py-1 px-2 rounded-md bg-green-100 font-semibold hover:bg-blue-100/50">
          {{ show_writing_tasks ? 'Hide' : 'Show' }} Writing Tasks <ChevronRightIcon class="inline h-4 w-4"></ChevronRightIcon>
        </button>

        <OverlayPanel ref="export_dialog">
          <ExportTableArea :collection_id="collection_id" :class_name="class_name">
          </ExportTableArea>
        </OverlayPanel>
      </div>

      <DataTable :value="collection_items" tableStyle="" scrollable scrollHeight="flex" class="min-h-0 overflow-x-auto">
          <Column header="Item">
            <template #body="slotProps">
              <CollectionItem
                :dataset_id="slotProps.data.dataset_id"
                :item_id="slotProps.data.item_id"
                :is_positive="slotProps.data.is_positive"
                class="w-[520px]">
              </CollectionItem>
            </template>
          </Column>
          <Column v-for="column in collection.columns" :header="false">
            <template #header="slotProps">
              <button class="rounded-md bg-gray-100 hover:bg-blue-100/50 py-1 px-2"
                @click="event => {selected_column = column; $refs.column_options.toggle(event)}">
                {{ column.name }}
              </button>
            </template>
            <template #body="slotProps">
              <CollectionTableCell :item="slotProps.data" :column="column"
                :current_extraction_processes="collection.current_extraction_processes">
              </CollectionTableCell>
            </template>
          </Column>
      </DataTable>

      <div class="flex flex-row items-center justify-center">
        <Paginator v-model:first="first_index" :rows="per_page" :total-records="item_count"
          class="mt-[0px]"></Paginator>
        <Dropdown v-model="order_by_field"
          :options="available_order_by_fields"
          optionLabel="name"
          optionValue="identifier"
          placeholder="Order By..."
          class="w-40 mr-2 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500" />
        <button @click="order_descending = !order_descending"
          class="w-8 h-8 text-sm text-gray-400 rounded bg-white border border-gray-300 hover:bg-gray-100">
          {{ order_descending ? '▼' : '▲' }}
        </button>
      </div>

      <OverlayPanel ref="column_options">
          <div class="w-[400px] flex flex-col gap-2">
            <!-- <h3 class="font-bold">{{ selected_column.name }}</h3> -->
            <div class="flex flex-row">
              <p class="flex-1">{{ selected_column.expression }}</p>
              <button
                @click="delete_column(selected_column.id); $refs.column_options.hide()"
                class="flex h-6 w-6 items-center justify-center rounded text-gray-400 hover:bg-gray-100 hover:text-red-500">
                <TrashIcon class="h-4 w-4"></TrashIcon>
              </button>
            </div>
            <p class="text-xs text-gray-500">{{ human_readable_source_fields(selected_column.source_fields) }}</p>
            <p class="text-xs text-gray-500">{{ human_readable_module_name(selected_column.module) }}</p>
            <div v-if="selected_column.module && selected_column.module !== 'notes'" class="flex flex-row gap-2">
              <button @click="extract_question(selected_column.id, true); $refs.column_options.hide()"
                class="flex-1 p-1 bg-gray-100 hover:bg-blue-100/50 rounded text-sm text-green-800">
                Extract <span class="text-gray-500">(current page)</span></button>
              <button @click="extract_question(selected_column.id, false); $refs.column_options.hide()"
                class="flex-1 p-1 bg-gray-100 hover:bg-blue-100/50 rounded text-sm text-green-800">
                Extract <span class="text-gray-500">(all)</span></button>
            </div>

            <div class="flex flex-row gap-2">
              <button @click="remove_results(selected_column.id, true)"
                class="flex-1 p-1 bg-gray-100 hover:bg-blue-100/50 rounded text-sm text-red-800">
                Remove results<br><span class="text-gray-500">(current page)</span></button>
              <button @click="remove_results(selected_column.id, false)"
                class="flex-1 p-1 bg-gray-100 hover:bg-blue-100/50 rounded text-sm text-red-800">
                Remove results<br><span class="text-gray-500">(all)</span></button>
            </div>
          </div>
      </OverlayPanel>
    </div>

    <WritingTaskArea v-if="show_writing_tasks" class="flex-none w-[500px]"
      :collection_id="collection_id" :class_name="class_name">
    </WritingTaskArea>

    <Dialog
      v-model:visible="show_details_dialog"
      :style="{'max-width': '650px', width: '650px'}"
      @hide="appState.selected_document_ds_and_id = null">
      <ObjectDetailsModal
        :initial_item="appState.get_item_by_ds_and_id(appState.selected_document_ds_and_id)"
        :dataset="appState.datasets[appState.selected_document_ds_and_id[0]]"
        :show_action_buttons="false"></ObjectDetailsModal>
    </Dialog>

  </div>

</template>

<style scoped>
</style>
