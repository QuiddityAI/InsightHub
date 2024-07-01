<script setup>
import {
  PencilIcon,
 } from "@heroicons/vue/24/outline"

import { useToast } from 'primevue/usetoast';

import SearchFilterList from "./SearchFilterList.vue"

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
  props: [],
  emits: [],
  data() {
    return {
      task_type_names: {
        'quick_search': 'Quick Search',
        'topic_overview': 'Topic Overview',
        'question': 'Question',
        'high_precision_search': 'High Precision Search',
        'custom_search': 'Custom Search',
      },
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
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
  <div class="flex flex-col bg-white shadow-sm rounded-md px-5 pt-2 pb-4">

    <div class="flex flex-row items-center">

      <!-- <h3 class="text-sm text-gray-500">
        {{ task_type_names[mapState.map_parameters?.search.task_type || 'quick_search'] }}</h3> -->
      <span v-if="mapState.map_parameters?.search.dataset_ids.length > 0"
        class="text-sm text-gray-500">
        {{ mapState.map_parameters?.search.dataset_ids.map(dataset_id => appState.datasets[dataset_id].name).join(', ') }}:
      </span>
      <span v-else class="text-sm text-gray-500">
        Loading...
      </span>
      <div class="flex-1"></div>
      <div class=" h-full flex flex-row items-center gap-2">
        <button class="h-full py-1 px-2 rounded-md bg-gray-100 text-sm text-gray-500  hover:bg-blue-100/50 hover:text-gray-700"
          v-tooltip.bottom="{ value: 'Edit search', showDelay: 400 }"
          @click="appState.open_search_edit_mode()">
          <PencilIcon class="w-4 h-4"></PencilIcon>
        </button>
        <button class="h-full py-1 px-2 rounded-md bg-gray-100 text-sm text-gray-500  hover:bg-blue-100/50 hover:text-gray-700"
          @click="appState.reset_search_box(); appState.reset_search_results_and_map()">
          New Search
        </button>
      </div>
    </div>

    <button v-for="(origin, index) in mapState.map_parameters?.search.origins"
      class="mb-1 flex flex-row items-center gap-2 text-sm text-gray-500 hover:text-blue-500"
      @click="appState.show_stored_map(origin.map_id)">
      ↳ <span v-html="origin.display_name"></span>
    </button>

    <div class="flex flex-row items-center justify-between">

      <h2 v-if="mapState.map_parameters?.search.search_type === 'external_input'"
        class="text-lg font-bold leading-none">
        {{ mapState.map_parameters?.search.all_field_query }}
      </h2>

      <h2 v-if="mapState.map_parameters?.search.search_type === 'cluster'"
        class="text-md font-bold">
        Cluster: {{ mapState.map_parameters?.search.origin_display_name }}
      </h2>

      <h2 v-if="mapState.map_parameters?.search.search_type === 'map_subset'"
        class="text-md font-bold">
        Custom Selection
      </h2>

      <h2 v-if="mapState.map_parameters?.search.search_type === 'similar_to_item'"
        class="text-md font-bold">
        Similar to: {{ mapState.map_parameters?.search.origin_display_name }}
      </h2>

      <h2 v-if="mapState.map_parameters?.search.search_type === 'global_map'"
        class="text-md font-bold">
        Overview: {{ mapState.map_parameters?.search.dataset_ids.map(dataset_id => appState.datasets[dataset_id].name).join(', ') }}
      </h2>

    </div>

    <SearchFilterList :show_filters_of_current_task="true"
      class="-ml-1">
    </SearchFilterList>
  </div>

</template>

<style scoped>
</style>
