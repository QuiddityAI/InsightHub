<script setup>
import { useToast } from 'primevue/usetoast';
import { httpClient, djangoClient } from "../../api/httpClient"
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { available_filter_operators } from '../../utils/utils'
const appState = useAppStateStore()
const mapState = useMapStateStore()
const toast = useToast()
</script>

<script>

export default {
  inject: ["eventBus"],
  props: ["filters"],
  emits: ["close"],
  data() {
    return {
      available_order_by_types: [
        { id: "score", title: "Relevancy" },
        // { id: "number_field", title: "Number Field" },
        // { id: "classifier", title: "Classifier" },
      ],
      selected_filter_field: null,
      selected_operator: null,
      filter_value: '',
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    available_filter_fields() {
      const dataset_ids = this.appStateStore.settings.search.dataset_ids
      const available_fields = {}
      for (const dataset_id of dataset_ids) {
        const dataset = this.appStateStore.datasets[dataset_id]
        for (const field of Object.values(dataset.schema.object_fields)) {
          if (!field.is_available_for_filtering) continue
          const index_params = field.index_parameters || {}
          const no_index_in_vector_db = index_params.no_index_in_vector_database || index_params.exclude_from_vector_database
          if (this.appStateStore.settings.search.retrieval_mode !== 'keyword' && no_index_in_vector_db) continue
          available_fields[field.identifier] = {
            identifier: field.identifier,
            dataset_id: dataset_id,  // for now, filters are applied to all matching fields in any dataset, but we need one dataset as a reference for the field description
            name: field.name || field.identifier,
          }
        }
      }
      available_fields['_descriptive_text_fields'] = {
        identifier: '_descriptive_text_fields',
        dataset_id: null,
        name: 'Descriptive Text*',
      }
      return Object.values(available_fields).sort((a, b) => a.identifier.localeCompare(b.identifier))
    },
    descriptive_text_field_details() {
      const dataset_ids = this.appStateStore.settings.search.dataset_ids
      const all_details = []
      for (const dataset_id of dataset_ids) {
        const dataset = this.appStateStore.datasets[dataset_id]
        const details = {
          dataset_name: dataset.name,
          descriptive_text_field_names: [],
        }
        for (const field_name of dataset.schema.descriptive_text_fields) {
          const field = dataset.schema.object_fields[field_name]
          if (!field.is_available_for_filtering) continue
          details.descriptive_text_field_names.push(field.name || field.identifier)
        }
        if (details.descriptive_text_field_names.length === 0) {
          details.descriptive_text_field_names.push('None')
        }
        all_details.push(details)
      }
      return all_details
    }
  },
  mounted() {
  },
  watch: {
  },
  methods: {
    add_filter() {
      if (!this.selected_filter_field || !this.selected_operator) {
        this.$toast.add({ severity: 'warn', summary: 'Missing field', detail: 'A field is missing', life: 2000 })
        return
      }
      this.filters.push({
        field: this.selected_filter_field.identifier,
        dataset_id: this.selected_filter_field.dataset_id,
        operator: this.selected_operator,
        value: this.filter_value,
      })
      this.$emit('close')
    },
  },
}
</script>

<template>
  <div>

    <!-- <div class="h-6 flex flex-row items-center gap-0 pl-1 rounded-md">
      <span class="pr-0 flex-none text-sm font-['Lexend'] font-normal text-gray-400">
        Order by: </span>
      <div class="w-32">
        <select
          v-model="appState.settings.search.order_by.type"
          class="w-full h-full rounded-md border-transparent bg-transparent pb-0 pl-1 pr-7 pt-0 text-ellipsis text-sm font-['Lexend'] font-normal text-gray-400 focus:border-blue-500 focus:ring-blue-500">
          <option v-for="item in available_order_by_types" :value="item.id" selected>
            {{ item.title }}
          </option>
        </select>
      </div>
    </div> -->

    <div class="my-2 flex items-stretch">
        <div class="flex-initial w-56">
          <select v-model="selected_filter_field"

            class="w-full h-full mr-4 text-sm text-gray-500 border-1 border-gray-300 rounded-l-md focus:border-blue-500 focus:ring-blue-500">
            <option :value="null">
              {{ $t('AddFilterMenu.field') }}
            </option>
            <option v-for="field in available_filter_fields" :value="field">
              {{ field.name }}
            </option>
          </select>
        </div>
        <div class="flex-initial w-40">
          <select v-model="selected_operator"
            class="w-full h-full mr-4 text-sm text-gray-500 border-1 border-gray-300 focus:border-blue-500 focus:ring-blue-500">
            <option :value="null">
              {{ $t('AddFilterMenu.operator') }}
            </option>
            <option v-for="field in available_filter_operators" :value="field.id">
              {{ field.title }}
            </option>
          </select>
        </div>
        <input
          v-model="filter_value"
          type="text"
          class="flex-auto border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
          placeholder="Value"
          @keyup.enter="add_filter()"/>
        <button
          class="rounded-r-md border-0 px-2 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
          type="button"
          @click="add_filter()">
          {{ $t('AddFilterMenu.add-filter') }}
        </button>
      </div>

      <h3 class="mt-4 text-sm text-gray-400">{{ $t('AddFilterMenu.note-not-all-filters-might-be-available-in-meaning-or-hybrid-mode') }}</h3>

      <h3 class="mt-3 text-sm text-gray-400">{{ $t('AddFilterMenu.descriptive-text-is-a-shortcut-for-these-fields') }}</h3>
      <ul>
        <li v-for="ds_fields in descriptive_text_field_details" class="text-sm text-gray-400">
          - {{ ds_fields.dataset_name }}: <em>{{ ds_fields.descriptive_text_field_names.join(", ") }}</em>
        </li>
      </ul>

      <!-- <p class="mt-3 text-sm text-gray-400">To check if a list has a certain value (e.g. if a tag is in a list of tags), use the 'is exact' or 'is not' operator.</p> -->

  </div>

</template>

<style scoped>
</style>
