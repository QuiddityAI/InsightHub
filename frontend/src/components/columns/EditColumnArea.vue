<script setup>

import {
  TrashIcon,
} from "@heroicons/vue/24/outline"

import { useToast } from 'primevue/usetoast';
import OverlayPanel from 'primevue/overlaypanel';
import Textarea from 'primevue/textarea';
import Checkbox from 'primevue/checkbox';

import { FieldType } from "../../utils/utils"
import { httpClient, djangoClient } from "../../api/httpClient"

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { useCollectionStore } from "../../stores/collection_store"

const appState = useAppStateStore()
const mapState = useMapStateStore()
const collectionStore = useCollectionStore()
const toast = useToast()

</script>

<script>

export default {
  inject: ["eventBus"],
  props: ["selected_column"],
  expose: ["toggle"],
  emits: [],
  data() {
    return {
      available_llm_models: [],
      remove_existing_content: false,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
    collection() {
      return this.collectionStore.collection
    },
    available_modules() {
      return this.appStateStore.column_modules
    },
  },
  mounted() {
    this.get_available_llm_models()
  },
  watch: {
  },
  methods: {
    toggle(event) {
      this.$refs.column_options.toggle(event)
    },
    delete_column(column_id) {
      const that = this
      if (!confirm("Are you sure you want to delete this column and all of the extraction results and notes?")) {
        return
      }
      const body = {
        column_id: column_id,
      }
      httpClient.post(`/api/v1/columns/delete_column`, body)
      .then(function (response) {
        that.collectionStore.collection.columns = that.collectionStore.collection.columns.filter((column) => column.id !== column_id)
      })
      .catch(function (error) {
        console.error(error)
      })
    },
    human_readable_source_fields(fields) {
      const available_source_fields = this.collectionStore.available_source_fields
      try {
        return fields.map((field) => available_source_fields.find((f) => f.identifier === field).name).join(", ")
      } catch (error) {
        console.error(error)
        return "?"
      }
    },
    human_readable_module_name(module_identifier) {
      return this.available_modules.find((m) => m.identifier === module_identifier)?.name
    },
    submit_changes() {
      const body = {
        column_id: this.selected_column.id,
        name: this.selected_column.name,
        expression: this.selected_column.expression,
        prompt_template: this.selected_column.prompt_template,
        auto_run_for_approved_items: this.selected_column.auto_run_for_approved_items,
        auto_run_for_candidates: this.selected_column.auto_run_for_candidates,
        parameters: this.selected_column.parameters,
      }
      httpClient.post(`/api/v1/columns/update_column`, body)
      .then((response) => {
        // this.$toast.add({ severity: 'success', summary: 'Column Updated', detail: 'The column has been updated.', life: 3000 });
      })
      .catch((error) => {
        console.error(error)
        this.$toast.add({ severity: 'error', summary: 'Error', detail: 'An error occurred while updating the column.', life: 3000 });
      })
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
  <OverlayPanel ref="column_options">
    <div class="w-[400px] flex flex-col gap-2">

      <div class="flex flex-row items-center gap-2">
        <Textarea class="flex-1 ring-0 border-0 min-h-0 text-sm font-bold text-gray-500" autoResize :rows="1" :pt="{ root: 'p-0 resize-none min-h-0', }"
          v-model="selected_column.name" @blur="submit_changes()" @keyup.enter="submit_changes()">
        </Textarea>
        <p class="text-xs text-gray-500"
          v-tooltip.top="{ value: 'Module used for this column', showDelay: 400 }">
          {{ human_readable_module_name(selected_column.module) }}
        </p>
        <p class="text-xs text-gray-500" v-if="selected_column.parameters?.language"
          v-tooltip.top="{ value: 'Language of the text to be generated', showDelay: 400 }">
          {{ selected_column.parameters?.language }}
        </p>
        <button
          @click="delete_column(selected_column.id); $refs.column_options.hide()"
          class="flex h-6 w-6 items-center justify-center rounded text-gray-400 hover:bg-gray-100 hover:text-red-500">
          <TrashIcon class="h-4 w-4"></TrashIcon>
        </button>
      </div>

      <div class="flex flex-row my-3" v-if="['llm', 'relevance', 'email'].includes(selected_column.module)">
        <Textarea class="flex-1 ring-0 border-0" autoResize :rows="1" :pt="{ root: 'p-0 resize-none', }"
          v-model="selected_column.expression" @blur="submit_changes()" @keyup.enter="submit_changes()">
        </Textarea>
      </div>

      <div class="flex flex-row" v-if="['llm', 'relevance', 'email'].includes(selected_column.module) && selected_column.prompt_template">
        <Textarea class="flex-1 ring-0 border-0 text-sm" :rows="5" :pt="{ root: 'p-0', }"
          v-model="selected_column.prompt_template" @blur="submit_changes()" @keyup.enter="submit_changes()">
        </Textarea>
      </div>

      <p class="text-xs text-gray-500"  v-if="!['notes'].includes(selected_column.module)">
        {{ human_readable_source_fields(selected_column.source_fields) }}
      </p>

      <div v-if="['llm', 'relevance'].includes(selected_column.module)"
        class="flex flex-row gap-2 items-center">
        <div class="flex-1 min-w-0">
          <select v-model="selected_column.parameters.model" @change="submit_changes()"
            class="w-full m-0 p-0 text-xs text-gray-500 border-0">
            <option v-for="model in available_llm_models" :value="model.model_id">{{ model.verbose_name }}</option>
          </select>
        </div>
      </div>

      <div class="flex flex-row gap-5 items-center" v-if="!['notes', 'item_field'].includes(selected_column.module)">
        <div class="flex flex-row items-center"
          v-tooltip.top="{ value: 'Execute this as soon as an item is approved' }">
          <Checkbox v-model="selected_column.auto_run_for_approved_items" :binary="true" @change="submit_changes()" />
          <button class="ml-2 text-xs text-gray-500"
            @click="selected_column.auto_run_for_approved_items = !selected_column.auto_run_for_approved_items">
            Auto-run for Approved Items
          </button>
        </div>
        <div class="flex flex-row items-center"
          v-tooltip.top="{ value: 'Execute this automatically for candidates (e.g. search results)' }">
          <Checkbox v-model="selected_column.auto_run_for_candidates" :binary="true" @change="submit_changes()" />
          <button class="ml-2 text-xs text-gray-500"
            @click="selected_column.auto_run_for_candidates = !selected_column.auto_run_for_candidates">
            Auto-run for Candidates
          </button>
        </div>
      </div>

      <div class="flex flex-row gap-5 items-center" v-if="!['notes', 'item_field'].includes(selected_column.module)">
        <div class="flex flex-row items-center"
          v-tooltip.top="{ value: 'Remove existing content (also manual edits) before processing using buttons below' }">
          <Checkbox v-model="remove_existing_content" :binary="true" />
          <button class="ml-2 text-xs text-gray-500"
            @click="remove_existing_content = !remove_existing_content">
            Remove existing content before processing
          </button>
        </div>
      </div>

      <div v-if="selected_column.module && selected_column.module !== 'notes'" class="flex flex-row gap-3 mt-2">
        <button @click="collectionStore.extract_question(selected_column.id, /*only_current_page*/ true, /*col_item*/ null, /*remove_content*/ remove_existing_content); $refs.column_options.hide()"
          class="flex-1 p-1 bg-gray-100 hover:bg-blue-100/50 rounded-lg text-sm text-green-800">
          Process this page <br> <span class="text-gray-500 text-xs">(empty cells)</span></button>
        <button @click="collectionStore.extract_question(selected_column.id, /*only_current_page*/ false, /*col_item*/ null, /*remove_content*/ remove_existing_content); $refs.column_options.hide()"
          class="flex-1 p-1 bg-gray-100 hover:bg-blue-100/50 rounded-lg text-sm text-green-800/70">
          Process all pages <br> <span class="text-gray-500 text-xs">(empty cells)</span></button>
      </div>
    </div>
  </OverlayPanel>
</template>

<style scoped>
</style>
