<script setup>
import {
  PencilIcon,
  NoSymbolIcon,
  ChevronUpIcon,
  StarIcon,
} from "@heroicons/vue/24/outline"

import Checkbox from 'primevue/checkbox';

import BorderlessButton from "../widgets/BorderlessButton.vue";
import SearchFilterList from "./SearchFilterList.vue";

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { useCollectionStore } from '../../stores/collection_store';
import { httpClient } from "../../api/httpClient"

const appState = useAppStateStore()
const mapState = useMapStateStore()
const collectionStore = useCollectionStore()

</script>

<script>

export default {
  inject: ["eventBus"],
  props: [],
  emits: ["edit_search_task"],
  data() {
    return {
      show_periodic_execution_settings: false,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
    retrieval_parameters() {
      return this.collectionStore.collection.most_recent_search_task?.retrieval_parameters
    }
  },
  mounted() {
    this.show_periodic_execution_settings = this.collectionStore.collection.most_recent_search_task?.run_on_new_items || false
  },
  watch: {
  },
  methods: {
  },
}
</script>

<template>
  <div class="w-full px-5 py-1 flex flex-col gap-1">
    <div class="flex flex-row items-center gap-4">

      <BorderlessButton v-if="collectionStore.collection.search_task_navigation_history.length >= 2"
        @click="collectionStore.run_previous_search_task"
        v-tooltip.bottom="{value: 'Go to the previous search result', showDelay: 400}"
        class="h-full -mr-3 -ml-3">
        <ChevronUpIcon class="h-5 w-5" />
      </BorderlessButton>

      <span class="flex-none text-blue-500">Search Mode:</span>

      <div>
        <span class="text-gray-700">
          {{ retrieval_parameters.query }}
        </span>
        <SearchFilterList
          :filters="retrieval_parameters.filters || []"
          :removable="false"
          class="-ml-1 mt-1 mb-1">
        </SearchFilterList>
      </div>

      <div class="flex-1"></div>

      <BorderlessButton @click="show_periodic_execution_settings = !show_periodic_execution_settings" class="py-1"
        :highlighted="show_periodic_execution_settings"
        v-tooltip.bottom="{value: 'Save / execute periodically', showDelay: 400}">
        <StarIcon class="h-5 w-5 inline" />
      </BorderlessButton>
      <BorderlessButton @click="$emit('edit_search_task')" class="py-1"
        v-tooltip.bottom="{value: 'Edit the search query and filters', showDelay: 400}">
        <PencilIcon class="h-5 w-5 inline" /> Edit
      </BorderlessButton>
      <BorderlessButton @click="collectionStore.exit_search_mode" class="py-1"
        v-tooltip.bottom="{value: 'Remove search results and show saved items', showDelay: 400}">
        <NoSymbolIcon class="h-5 w-5 inline" /> Exit
      </BorderlessButton>
    </div>

    <div v-if="show_periodic_execution_settings" class="flex flex-row items-center gap-4">
      <div class="flex flex-row items-center">
        <Checkbox v-model="collectionStore.collection.most_recent_search_task.run_on_new_items"
          @change="collectionStore.commit_most_recent_search_task_execution_settings()"
          class="" :binary="true" />
        <button class="ml-2 text-xs text-gray-500"
          @click="collectionStore.collection.most_recent_search_task.run_on_new_items = !collectionStore.collection.most_recent_search_task.run_on_new_items; collectionStore.commit_most_recent_search_task_execution_settings()">
          Run for new items
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
</style>
